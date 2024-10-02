from decimal import Decimal

from djtools.assincrono import task
from djtools.templatetags.filters import format_
from djtools.utils import XlsResponse
from saude.models import HipoteseDiagnostica, IntervencaoEnfermagem, ProcessoSaudeDoenca


@task('Exportar Antropometria para XLS')
def graficos_antropometria_to_xls(registros, task=None):
    colunas = []
    rows = []
    colunas.append('#')
    colunas.append('Nome')
    colunas.append('Matrícula')
    colunas.append('Curso')
    colunas.append('Turma')
    colunas.append('IMC')
    rows.append(colunas)

    contador = 1
    for registro in task.iterate(registros):
        row = [contador]
        aluno = registro.atendimento.aluno
        row.append(format_(aluno.pessoa_fisica.nome))

        row.append(format_(aluno.matricula))

        row.append(format_(aluno.curso_campus))
        turma = '-'
        if aluno.get_ultima_matricula_periodo():
            turma = aluno.get_ultima_matricula_periodo().get_codigo_turma()
        row.append(format_(turma))
        estatura_imc = Decimal((registro.estatura / 100.0) * (registro.estatura / 100.0))
        if estatura_imc:
            imc = Decimal(registro.peso) / estatura_imc
        else:
            imc = Decimal('0.0')
        row.append(format_(imc))
        rows.append(row)
        contador += 1

    return XlsResponse(rows, processo=task)


@task('Exportar Dados de Acuidade Visual para XLS')
def exportar_graficos_acuidade_visual_to_xls(registros, task=None):
    colunas = []
    rows = []
    colunas.append('#')
    colunas.append('Nome')
    colunas.append('Matrícula')
    colunas.append('Curso')
    colunas.append('Turma')
    colunas.append('Olho Esquerdo')
    colunas.append('Olho Direito')
    colunas.append('Com Correção')
    rows.append(colunas)

    contador = 1
    for registro in task.iterate(registros):
        row = [contador]
        aluno = registro.atendimento.aluno
        if aluno:
            row.append(format_(aluno.pessoa_fisica.nome))

            row.append(format_(aluno.matricula))

            row.append(format_(aluno.curso_campus))
            turma = '-'
            if aluno.get_ultima_matricula_periodo():
                turma = aluno.get_ultima_matricula_periodo().get_codigo_turma()
            row.append(format_(turma))

            row.append(registro.olho_esquerdo)
            row.append(registro.olho_direito)
            if registro.com_correcao:
                correcao = 'Sim'
            else:
                correcao = 'Não'
            row.append(correcao)
            rows.append(row)
            contador += 1

    return XlsResponse(rows, processo=task)


@task('Exportar Dados de Saúde e Doenças para XLS')
def graficos_saude_doenca_to_xls(registros, task=None):
    ids_alunos = list()
    ids_registros = list()
    for registro in registros:
        if registro.atendimento.prontuario.vinculo_id not in ids_alunos:
            ids_registros.append(registro.id)
            ids_alunos.append(registro.atendimento.prontuario.vinculo_id)

    registros = registros.filter(id__in=ids_registros)
    colunas = []
    rows = []
    colunas.append('#')
    colunas.append('Nome')
    colunas.append('Matrícula')
    colunas.append('Curso')
    colunas.append('Turma')
    colunas.append('Já fez alguma cirurgia')
    colunas.append('Que cirurgia')
    colunas.append('Quanto tempo da cirurgia')
    colunas.append('Histórico de hemorragia')
    colunas.append('Há quanto tempo apresentou hemorragia')
    colunas.append('Alergia a alimentos')
    colunas.append('Quais alimentos')
    colunas.append('Doenças Prévias')
    colunas.append('Quais Doenças Prévias')
    colunas.append('Alergia a medicamentos')
    colunas.append('Quais medicamentos')
    colunas.append('Faz uso de medicamentos rotineiramente')
    colunas.append('Usa quais medicamentos')
    colunas.append('Tem Plano de Saúde')
    colunas.append('Tem Plano Odontológico')
    colunas.append('Já teve transtorno psiquiátrico?')
    colunas.append('Qual transtorno psiquiátrico?')
    colunas.append('Já passou por psiquiatra?')
    colunas.append('Tempo na psiquiatria')
    colunas.append('Há quanto tempo esteve no psiquiatra')
    colunas.append('Teve lesões ortopédicas')
    colunas.append('Quais lesões ortopédicas')
    colunas.append('Sofre de alguma doença crônica')
    colunas.append('Gestante')
    colunas.append('Problemas Auditivos')
    colunas.append('Qual problema auditivo')
    rows.append(colunas)
    contador = 1
    for registro in task.iterate(registros):
        row = [contador]
        curso = '-'
        turma = '-'
        pessoa = registro.atendimento.aluno
        if not pessoa:
            pessoa = registro.atendimento.servidor
        if not pessoa:
            pessoa = registro.atendimento.prestador_servico
        if not pessoa:
            pessoa = registro.atendimento.pessoa_externa
        if pessoa:
            if registro.atendimento.aluno:
                curso = pessoa.curso_campus
                if pessoa.get_ultima_matricula_periodo():
                    turma = pessoa.get_ultima_matricula_periodo().get_codigo_turma()
            row.append(format_(pessoa.pessoa_fisica.nome))
            row.append(format_(pessoa.matricula))
            row.append(format_(curso))
            row.append(format_(turma))
            row.append(registro.fez_cirurgia)
            row.append(registro.que_cirurgia)
            row.append(registro.tempo_cirurgia)
            row.append(registro.hemorragia)
            row.append(registro.tempo_hemorragia)
            row.append(registro.alergia_alimentos)
            row.append(registro.que_alimentos)
            row.append(registro.doencas_previas)
            row.append(registro.que_doencas_previas)
            row.append(registro.alergia_medicamentos)
            row.append(registro.que_medicamentos)
            row.append(registro.usa_medicamentos)
            row.append(registro.usa_que_medicamentos)
            row.append(registro.tem_plano_saude)
            row.append(registro.tem_plano_odontologico)
            row.append(registro.transtorno_psiquiatrico)
            row.append(registro.qual_transtorno_psiquiatrico)
            row.append(registro.psiquiatra)
            row.append(registro.duracao_psiquiatria)
            row.append(registro.tempo_psiquiatria)
            row.append(registro.lesoes_ortopedicas)
            row.append(registro.quais_lesoes_ortopedicas)
            doencas_cronicas = ''
            for doenca in registro.doencas_cronicas.all():
                doencas_cronicas += '{}, '.format(doenca.nome)
            row.append(doencas_cronicas)
            row.append(registro.gestante)
            row.append(registro.problema_auditivo)
            row.append(registro.qual_problema)
            rows.append(row)
            contador += 1

    return XlsResponse(rows, processo=task)


@task('Exportar Dados de Hábitos de Vida para XLS')
def graficos_habitos_vida_to_xls(registros, task=None):
    ids_alunos = list()
    ids_registros = list()
    for registro in registros:
        if registro.atendimento.prontuario.vinculo_id not in ids_alunos:
            ids_registros.append(registro.id)
            ids_alunos.append(registro.atendimento.prontuario.vinculo_id)

    registros = registros.filter(id__in=ids_registros)
    colunas = []
    rows = []
    colunas.append('#')
    colunas.append('Nome')
    colunas.append('Matrícula')
    colunas.append('Curso')
    colunas.append('Turma')
    colunas.append('Pratica atividade física')
    colunas.append('Qual atividade')
    colunas.append('Qual a frequência semanal')
    colunas.append('Duração da atividade física')
    colunas.append('Fuma')
    colunas.append('Número de cigarros por dia')
    colunas.append('Faz uso ou já usou drogas ilícitas')
    colunas.append('Quais drogas')
    colunas.append('Outras drogas')
    colunas.append('Ingere bebidas alcoólicas')
    colunas.append('Frequência mínima de ingestão de bebidas alcoólicas')
    colunas.append('Tem dificuldade para dormir')
    colunas.append('Horas de sono diárias')
    colunas.append('Quantas refeições faz por dia')
    colunas.append('Tem vida sexual ativa')
    colunas.append('Faz uso de algum método contraceptivo')
    colunas.append('Qual método contraceptivo')
    colunas.append('Faz uso da internet?')
    colunas.append('Qual o tempo de uso')
    colunas.append('Objetivo do uso')
    rows.append(colunas)
    contador = 1
    for registro in task.iterate(registros):
        row = [contador]
        curso = '-'
        turma = '-'
        pessoa = registro.atendimento.aluno
        if not pessoa:
            pessoa = registro.atendimento.servidor
        if not pessoa:
            pessoa = registro.atendimento.prestador_servico
        if not pessoa:
            pessoa = registro.atendimento.pessoa_externa
        if pessoa:
            if registro.atendimento.aluno:
                curso = pessoa.curso_campus
                if pessoa.get_ultima_matricula_periodo():
                    turma = pessoa.get_ultima_matricula_periodo().get_codigo_turma()
            row.append(format_(pessoa.pessoa_fisica.nome))
            row.append(format_(pessoa.matricula))
            row.append(format_(curso))
            row.append(format_(turma))
            row.append(registro.atividade_fisica)
            row.append(registro.qual_atividade)
            row.append(registro.frequencia_semanal)
            row.append(registro.duracao_atividade)
            row.append(registro.fuma)
            row.append(registro.frequencia_fumo)
            row.append(registro.usa_drogas)
            que_drogas = ''
            for droga in registro.que_drogas.all():
                que_drogas += '{}, '.format(droga.nome)
            row.append(que_drogas)
            row.append(registro.outras_drogas)
            row.append(registro.bebe)
            row.append(registro.frequencia_bebida)
            row.append(registro.dificuldade_dormir)
            row.append(registro.horas_sono)
            row.append(registro.refeicoes_por_dia)
            row.append(registro.vida_sexual_ativa)
            row.append(registro.metodo_contraceptivo)
            qual_metodo_contraceptivo = ''
            for metodo in registro.qual_metodo_contraceptivo.all():
                qual_metodo_contraceptivo += '{}, '.format(metodo.nome)
            row.append(qual_metodo_contraceptivo)
            row.append(registro.uso_internet)
            row.append(registro.tempo_uso_internet)
            row.append(registro.objetivo_uso_internet)
            rows.append(row)
            contador += 1

    return XlsResponse(rows, processo=task)


@task('Exportar Dados de Desenvolvimento Pessoal para XLS')
def graficos_desenvolvimento_pessoal_to_xls(registros, task=None):
    colunas = []
    rows = []
    colunas.append('#')
    colunas.append('Nome')
    colunas.append('Matrícula')
    colunas.append('Curso')
    colunas.append('Turma')
    colunas.append('Tem Problema de Apredizado')
    colunas.append('Qual o Problema')
    colunas.append('Origem do Problema')
    rows.append(colunas)
    contador = 1
    for registro in task.iterate(registros):
        row = [contador]
        curso = '-'
        turma = '-'
        pessoa = registro.atendimento.aluno
        if not pessoa:
            pessoa = registro.atendimento.servidor
        if not pessoa:
            pessoa = registro.atendimento.prestador_servico
        if not pessoa:
            pessoa = registro.atendimento.pessoa_externa
        if pessoa:
            if registro.atendimento.aluno:
                curso = pessoa.curso_campus
                if pessoa.get_ultima_matricula_periodo():
                    turma = pessoa.get_ultima_matricula_periodo().get_codigo_turma()
            row.append(format_(pessoa.pessoa_fisica.nome))
            row.append(format_(pessoa.matricula))
            row.append(format_(curso))
            row.append(format_(turma))
            tem_problema = 'Não'
            qual_problema = '-'
            origem_problema = '-'
            if registro.problema_aprendizado:
                tem_problema = 'Sim'
                qual_problema = registro.qual_problema_aprendizado
                origem_problema = registro.origem_problema
            row.append(tem_problema)
            row.append(qual_problema)
            row.append(origem_problema)
            rows.append(row)
            contador += 1

    return XlsResponse(rows, processo=task)


@task('Exportar Dados de Exames Fisicos para XLS')
def graficos_exame_fisico_to_xls(registros, task=None):
    colunas = []
    rows = []
    colunas.append('#')
    colunas.append('Nome')
    colunas.append('Matrícula')
    colunas.append('Curso')
    colunas.append('Turma')
    colunas.append('Ectoscopia alterada')
    colunas.append('Alteração na ectoscopia')
    colunas.append('Aparelho cardiovascular alterado')
    colunas.append('Alteração no aparelho cardiovascular')
    colunas.append('Aparelho respiratório alterado')
    colunas.append('Alteração no aparelho respiratório')
    colunas.append('Abdome alterado')

    colunas.append('Alteração no abdome')
    colunas.append('Membros inferiores alterados')
    colunas.append('Alteração nos membros inferiores')
    colunas.append('Membros superiores alterados')
    colunas.append('Alteração nos membros superiores')
    colunas.append('Outros órgãos/sistemas alterados')
    colunas.append('Descrição das outras alterações')
    rows.append(colunas)

    contador = 1
    for registro in task.iterate(registros):
        row = [contador]
        curso = '-'
        turma = '-'
        pessoa = registro.atendimento.aluno
        if not pessoa:
            pessoa = registro.atendimento.servidor
        if not pessoa:
            pessoa = registro.atendimento.prestador_servico
        if not pessoa:
            pessoa = registro.atendimento.pessoa_externa
        if pessoa:
            if registro.atendimento.aluno:
                curso = pessoa.curso_campus
                if pessoa.get_ultima_matricula_periodo():
                    turma = pessoa.get_ultima_matricula_periodo().get_codigo_turma()
            row.append(format_(pessoa.pessoa_fisica.nome))
            row.append(format_(pessoa.matricula))
            row.append(format_(curso))
            row.append(format_(turma))
            row.append(registro.ectoscopia_alterada)
            row.append(registro.alteracao_ectoscopia)
            row.append(registro.acv_alterado)
            row.append(registro.alteracao_acv)
            row.append(registro.ar_alterado)
            row.append(registro.alteracao_ar)
            row.append(registro.abdome_alterado)
            row.append(registro.alteracao_abdome)
            row.append(registro.mmi_alterados)
            row.append(registro.alteracao_mmi)
            row.append(registro.mms_alterados)
            row.append(registro.alteracao_mms)
            row.append(registro.outras_alteracoes)
            row.append(registro.outras_alteracoes_descricao)

            rows.append(row)
            contador += 1

    return XlsResponse(rows, processo=task)


@task('Exportando Dados de Percepção de Saúde Buscal para XLS')
def graficos_percepcao_saude_bucal_to_xls(registros, task=None):
    colunas = []
    rows = []
    colunas.append('#')
    colunas.append('Nome')
    colunas.append('Matrícula')
    colunas.append('Curso')
    colunas.append('Turma')
    colunas.append('Quantas vezes usou fio dental na última semana?')
    colunas.append('Na última semana quantos dias consumiu doces, balas, bolos ou refrigerantes?')
    colunas.append('Usa prótese?')
    colunas.append('Usa aparelho ortodôntico?')
    colunas.append('Já foi a um dentista anteriormente')
    colunas.append('Quanto tempo faz que foi a última vez ao dentista')
    colunas.append('Nos últimos 6 meses teve alguma dificuldade relacionada à boca, dente, prótese ou aparelho ortodôntico que lhe causou alguma dificuldade')
    colunas.append('Grau de dificuldade em sorrir')
    colunas.append('Qual motivo você atribui como responsável?')
    colunas.append('Grau de dificuldade em falar')
    colunas.append('Qual motivo você atribui como responsável?')
    colunas.append('Grau de dificuldade em comer')
    colunas.append('Qual motivo você atribui como responsável?')
    colunas.append('Grau de dificuldade em relacionar-se socialmente')
    colunas.append('Qual motivo você atribui como responsável?')
    colunas.append('Grau de dificuldade em manter o humor habitual')
    colunas.append('Qual motivo você atribui como responsável?')
    colunas.append('Grau de dificuldade em estudar')
    colunas.append('Qual motivo você atribui como responsável?')
    colunas.append('Grau de dificuldade em trabalhar')
    colunas.append('Qual motivo você atribui como responsável?')
    colunas.append('Grau de dificuldade em higienizar a boca')
    colunas.append('Qual motivo você atribui como responsável?')
    colunas.append('Grau de dificuldade em dormir')
    colunas.append('Qual motivo você atribui como responsável?')
    rows.append(colunas)

    contador = 1
    for registro in task.iterate(registros):
        row = [contador]
        curso = '-'
        turma = '-'
        pessoa = registro.atendimento.aluno
        if not pessoa:
            pessoa = registro.atendimento.servidor
        if not pessoa:
            pessoa = registro.atendimento.prestador_servico
        if not pessoa:
            pessoa = registro.atendimento.pessoa_externa
        if pessoa:
            if registro.atendimento.aluno:
                curso = pessoa.curso_campus
                if pessoa.get_ultima_matricula_periodo():
                    turma = pessoa.get_ultima_matricula_periodo().get_codigo_turma()
            row.append(format_(pessoa.pessoa_fisica.nome))
            row.append(format_(pessoa.matricula))
            row.append(format_(curso))
            row.append(format_(turma))
            row.append(registro.qtd_vezes_fio_dental_ultima_semana)
            row.append(registro.qtd_dias_consumiu_doce_ultima_semana)
            row.append(registro.usa_protese)
            row.append(registro.usa_aparelho_ortodontico)
            row.append(registro.foi_dentista_anteriormente)
            row.append(registro.tempo_ultima_vez_dentista)
            row.append(registro.dificuldades)
            row.append(registro.grau_dificuldade_sorrir)
            row.append(registro.motivo_dificuldade_sorrir)
            row.append(registro.grau_dificuldade_falar)
            row.append(registro.motivo_dificuldade_falar)
            row.append(registro.grau_dificuldade_comer)
            row.append(registro.motivo_dificuldade_comer)
            row.append(registro.grau_dificuldade_relacionar)
            row.append(registro.motivo_dificuldade_relacionar)
            row.append(registro.grau_dificuldade_manter_humor)
            row.append(registro.motivo_dificuldade_manter_humor)
            row.append(registro.grau_dificuldade_estudar)
            row.append(registro.motivo_dificuldade_estudar)
            row.append(registro.grau_dificuldade_trabalhar)
            row.append(registro.motivo_dificuldade_trabalhar)
            row.append(registro.grau_dificuldade_higienizar)
            row.append(registro.motivo_dificuldade_higienizar)
            row.append(registro.grau_dificuldade_dormir)
            row.append(registro.motivo_dificuldade_dormir)
            rows.append(row)
            contador += 1

    return XlsResponse(rows, processo=task)


@task('Exportar Dados de Atendimentos Odontológicos para XLS')
def relatorios_atendimentos_odontologicos_to_xls(atendimentos, task=None):
    rows = [
        [
            '#',
            'Nome',
            'Sexo',
            'Idade',
            'CPO-D Médio',
            'Dentes Cariados',
            'Dentes Perdidos',
            'Dentes Restaurados',
            'S1',
            'S2',
            'S3',
            'S4',
            'S5',
            'S6',
            'S1-S3',
            'S4-S6',
            'S1-S6',
            'Lábios',
            'Lingua',
            'Assoalho',
            'Mucosa Jugal',
            'Palato Duro',
            'Palato Mole',
            'Rebordo',
            'Cadeia Ganglionar',
            'Tonsilas Palatinas',
            'Atm',
            'Oclusão',
        ]
    ]

    contador = 1

    for atendimento in task.iterate(atendimentos):
        total = c = p = o = '-'
        tem_odontograma = atendimento.get_odontograma()
        if tem_odontograma:
            total, c, p, o = tem_odontograma.get_indice_cpod()
        labios = '-'
        lingua = '-'
        assoalho = '-'
        mucosa_jugal = '-'
        palato_duro = '-'
        palato_mole = '-'
        rebordo = '-'
        cadeia_ganglionar = '-'
        tonsilas_palatinas = '-'
        atm = '-'
        oclusao = '-'

        if atendimento.get_alteracoes_estomatologicas():
            labios = atendimento.get_alteracoes_estomatologicas().labios
            lingua = atendimento.get_alteracoes_estomatologicas().lingua
            assoalho = atendimento.get_alteracoes_estomatologicas().assoalho
            mucosa_jugal = atendimento.get_alteracoes_estomatologicas().mucosa_jugal
            palato_duro = atendimento.get_alteracoes_estomatologicas().palato_duro
            palato_mole = atendimento.get_alteracoes_estomatologicas().palato_mole
            rebordo = atendimento.get_alteracoes_estomatologicas().rebordo
            cadeia_ganglionar = atendimento.get_alteracoes_estomatologicas().cadeia_ganglionar
            tonsilas_palatinas = atendimento.get_alteracoes_estomatologicas().tonsilas_palatinas
            atm = atendimento.get_alteracoes_estomatologicas().atm
            oclusao = atendimento.get_alteracoes_estomatologicas().oclusao

        row = [
            contador,
            format_(atendimento.prontuario.vinculo.pessoa.nome),
            format_(atendimento.prontuario.vinculo.pessoa.pessoafisica.sexo),
            format_(atendimento.prontuario.vinculo.pessoa.pessoafisica.idade),
            format_(total),
            format_(c),
            format_(p),
            format_(o),
            format_(atendimento.get_exames_periodontais_s1()),
            format_(atendimento.get_exames_periodontais_s2()),
            format_(atendimento.get_exames_periodontais_s3()),
            format_(atendimento.get_exames_periodontais_s4()),
            format_(atendimento.get_exames_periodontais_s5()),
            format_(atendimento.get_exames_periodontais_s6()),
            format_(atendimento.get_exames_periodontais_s1_s3()),
            format_(atendimento.get_exames_periodontais_s4_s6()),
            format_(atendimento.get_exames_periodontais_s1_s6()),
            format_(labios),
            format_(lingua),
            format_(assoalho),
            format_(mucosa_jugal),
            format_(palato_duro),
            format_(palato_mole),
            format_(rebordo),
            format_(cadeia_ganglionar),
            format_(tonsilas_palatinas),
            format_(atm),
            format_(oclusao),
        ]
        rows.append(row)
        contador += 1
    return XlsResponse(rows, processo=task)


@task('Exportar Relatório de Atendimentos Médicos e Enfermagem para XLS')
def relatorio_atendimento_medico_enfermagem_to_xls(registros, task=None):
    colunas = []
    rows = []
    colunas.append('#')
    colunas.append('Nome')
    colunas.append('Matrícula')
    colunas.append('Curso')
    colunas.append('Turma')
    colunas.append('CID-10 por Capítulo')
    colunas.append('Intervenções de Enfermagem')
    colunas.append('Alergias Medicamentosas e Alimentares')
    rows.append(colunas)
    contador = 1
    for registro in task.iterate(registros):
        row = [contador]
        aluno = registro.aluno
        row.append(format_(aluno.pessoa_fisica.nome))

        row.append(format_(aluno.matricula))

        row.append(format_(aluno.curso_campus))
        turma = '-'
        if aluno.get_ultima_matricula_periodo():
            turma = aluno.get_ultima_matricula_periodo().get_codigo_turma()
        row.append(format_(turma))
        lista_cid = list()

        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='A00', cid__codigo__lte='B99').count()
        if qtd:
            lista_cid.append('Capítulo I - Algumas doenças infecciosas e parasitárias: {}'.format(qtd))

        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='C00', cid__codigo__lte='D48').count()
        if qtd:
            lista_cid.append('Capítulo II - Neoplasias [tumores]: {}'.format(qtd))

        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='D50', cid__codigo__lte='D89').count()
        if qtd:
            lista_cid.append('Capítulo III - Doenças do sangue e dos órgãos hematopoéticos e alguns transtornos imunitários: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='E00', cid__codigo__lte='E90').count()
        if qtd:
            lista_cid.append('Capítulo IV - Doenças endócrinas, nutricionais e metabólicas: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='F00', cid__codigo__lte='F99').count()
        if qtd:
            lista_cid.append('Capítulo V - Transtornos mentais e comportamentais: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='G00', cid__codigo__lte='G99').count()
        if qtd:
            lista_cid.append('Capítulo VI - Doenças do sistema nervoso: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='H00', cid__codigo__lte='H59').count()
        if qtd:
            lista_cid.append('Capítulo VII - Doenças do olho e anexos: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='H60', cid__codigo__lte='H95').count()
        if qtd:
            lista_cid.append('Capítulo VIII - Doenças do ouvido e da apófise mastóide: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='I00', cid__codigo__lte='I99').count()
        if qtd:
            lista_cid.append('Capítulo IX - Doenças do aparelho circulatório: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='J00', cid__codigo__lte='J99').count()
        if qtd:
            lista_cid.append('Capítulo X - Doenças do aparelho respiratório: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='K00', cid__codigo__lte='K93').count()
        if qtd:
            lista_cid.append('Capítulo XI - Doenças do aparelho digestivo: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='L00', cid__codigo__lte='L99').count()
        if qtd:
            lista_cid.append('Capítulo XII - Doenças da pele e do tecido subcutâneo: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='M00', cid__codigo__lte='M99').count()
        if qtd:
            lista_cid.append('Capítulo XIII - Doenças do sistema osteomuscular e do tecido conjuntivo: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='N00', cid__codigo__lte='N99').count()
        if qtd:
            lista_cid.append('Capítulo XIV - Doenças do aparelho geniturinário: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='O00', cid__codigo__lte='O99').count()
        if qtd:
            lista_cid.append('Capítulo XV - Gravidez, parto e puerpério: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='P00', cid__codigo__lte='P96').count()
        if qtd:
            lista_cid.append('Capítulo XVI - Algumas afecções originadas no período perinatal: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='Q00', cid__codigo__lte='Q99').count()
        if qtd:
            lista_cid.append('Capítulo XVII - Malformações congênitas, deformidades e anomalias cromossômicas: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='R00', cid__codigo__lte='R99').count()
        if qtd:
            lista_cid.append('Capítulo XVIII - Sintomas, sinais e achados anormais de exames clínicos e de laboratório, não classificados em outra parte: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='S00', cid__codigo__lte='T98').count()
        if qtd:
            lista_cid.append('Capítulo XIX - Lesões, envenenamento e algumas outras conseqüências de causas externas: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='V01', cid__codigo__lte='Y98').count()
        if qtd:
            lista_cid.append('Capítulo XX - Causas externas de morbidade e de mortalidade: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='Z00', cid__codigo__lte='Z99').count()
        if qtd:
            lista_cid.append('Capítulo XXI - Fatores que influenciam o estado de saúde e o contato com os serviços de saúde: {}'.format(qtd))
        qtd = HipoteseDiagnostica.objects.filter(atendimento=registro, cid__codigo__gte='U04', cid__codigo__lte='U99').count()
        if qtd:
            lista_cid.append('Capítulo XXII - Códigos para propósitos especiais: {}'.format(qtd))

        row.append(', '.join(lista_cid))
        lista_intervencao = list()
        for item in IntervencaoEnfermagem.objects.filter(atendimento=registro):
            lista_intervencao.append(item.procedimento_enfermagem.denominacao)
        row.append(', '.join(lista_intervencao))

        lista_alergias = list()
        for item in ProcessoSaudeDoenca.objects.filter(atendimento=registro):
            if item.que_alimentos:
                lista_alergias.append(item.que_alimentos)
            if item.que_medicamentos:
                lista_alergias.append(item.que_medicamentos)
        row.append(', '.join(lista_alergias))
        rows.append(row)
        contador += 1

    return XlsResponse(rows, processo=task)


@task('Exportar Lista de Alunos para XLS')
def lista_alunos_to_xls(atendimentos, ver_nome, ver_matricula, ver_curso, ver_turma, ver_rg, ver_cpf, ver_alergia_alimentos, ver_alergia_medicamentos, task=None):
    colunas = []
    rows = []
    conta_atributos = 0
    colunas.append('#')
    if ver_nome:
        colunas.append('Nome')
        conta_atributos += 1
    if ver_matricula:
        colunas.append('Matrícula')
        conta_atributos += 1
    if ver_curso:
        colunas.append('Curso')
        conta_atributos += 1
    if ver_turma:
        colunas.append('Turma')
        conta_atributos += 1
    if ver_rg:
        colunas.append('RG')
        conta_atributos += 1
    if ver_cpf:
        colunas.append('CPF')
        conta_atributos += 1
    if ver_alergia_alimentos:
        colunas.append('Alergia à Alimentos')
        conta_atributos += 1
    if ver_alergia_medicamentos:
        colunas.append('Alergia à Medicamentos')
        conta_atributos += 1
    rows.append(colunas)
    contador = 1
    for atendimento in task.iterate(atendimentos.distinct()):
        row = [contador]
        processo_saude = atendimento.get_processo_saude_doenca()
        if ver_nome:
            row.append(format_(atendimento.aluno.pessoa_fisica.nome))
        if ver_matricula:
            row.append(format_(atendimento.aluno.matricula))
        if ver_curso:
            row.append(format_(atendimento.aluno.curso_campus))
        if ver_turma:
            row.append(format_(atendimento.aluno.matricula))
        if ver_rg:
            row.append(format_(atendimento.aluno.pessoa_fisica.rg))
        if ver_cpf:
            row.append(format_(atendimento.aluno.pessoa_fisica.cpf.replace('.', '').replace('-', '')))
        if ver_alergia_alimentos:
            row.append(format_(processo_saude.que_alimentos))
        if ver_alergia_medicamentos:
            row.append(format_(processo_saude.que_medicamentos))
        rows.append(row)
        contador += 1

    return XlsResponse(rows, processo=task)
