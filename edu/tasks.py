import csv
import datetime
import operator
import os
import re
import tempfile
from django.conf import settings
from django.core.exceptions import ValidationError
from time import sleep

import xlrd
import xlwt
from django.db import transaction
from xlutils.copy import copy

from django.db.models import Count
from djtools.assincrono import task
from djtools.models import Task
from djtools.templatetags.filters import format_, getattrr
from djtools.testutils import running_tests
from djtools.utils import XlsResponse, CsvResponse, mask_cpf, similaridade
from djtools.utils.python import to_ascii
from edu import censup, educacenso, q_academico
from edu.models import SituacaoMatricula, MatriculaPeriodo, Modalidade, PedidoMatriculaDiario, SituacaoMatriculaPeriodo, \
    Diario, RegistroConvocacaoENADE, CursoCampus, Professor, NivelEnsino, Turno, MatriculaDiario
from edu.models.alunos import Aluno


@task('Fechar Período')
def fechar_periodo(confirmado, forcar_fechamento, matriculas_periodo, diarios, querystring, task=None):
    if confirmado:
        task.count(matriculas_periodo, diarios)
        for matricula_periodo in task.iterate(matriculas_periodo):
            matricula_periodo.fechar_periodo_letivo(forcar_fechamento)

        for diario in task.iterate(diarios):
            diario.fechar()
    task.finalize('Período fechado com sucesso.', '/edu/fechar_periodo_letivo/?{}&finalize=1'.format(querystring))


@task('Abrir Período')
def abrir_periodo(diarios, matriculas_periodo, querystring, task=None):
    task.count(diarios, matriculas_periodo)

    for diario in task.iterate(diarios):
        diario.abrir()

    for matricula_periodo in task.iterate(matriculas_periodo):
        matricula_periodo.abrir_periodo_letivo()

    task.finalize('Período aberto com sucesso.', '/edu/abrir_periodo_letivo/?{}&finalize=1'.format(querystring))


@task('Migrar Alunos')
def migrar_alunos(matriculas, matriz_id, ano_letivo, periodo_letivo, task=None):
    dao = running_tests() and q_academico.MockDAO() or q_academico.DAO()
    dao.importar_historico_resumo(matriculas, matriz_id, ano_letivo, periodo_letivo, task=task, validacao=False)


@task('Atualizar Lista de Convocação - ENADE')
def atulizar_lista_convocacao_enade(alunos, convocao_enade, task=None):
    for aluno in task.iterate(alunos):
        percentual_ch_componentes_cumprido = aluno.get_percentual_ch_componentes_cumpridos()
        qs_registro = RegistroConvocacaoENADE.objects.filter(aluno=aluno, convocacao_enade=convocao_enade)

        if qs_registro.exists():
            if aluno.ano_letivo.pk == convocao_enade.ano_letivo.pk and (
                convocao_enade.percentual_minimo_ingressantes <= percentual_ch_componentes_cumprido <= convocao_enade.percentual_maximo_ingressantes
            ):
                obj = qs_registro[0]
                obj.percentual_ch_cumprida = percentual_ch_componentes_cumprido
                obj.tipo_convocacao = RegistroConvocacaoENADE.TIPO_CONVOCACAO_INGRESSANTE
                obj.save()
            elif convocao_enade.percentual_minimo_concluintes <= percentual_ch_componentes_cumprido <= convocao_enade.percentual_maximo_concluintes:
                obj = qs_registro[0]
                obj.percentual_ch_cumprida = percentual_ch_componentes_cumprido
                obj.tipo_convocacao = RegistroConvocacaoENADE.TIPO_CONVOCACAO_CONCLUINTE
                obj.save()
        else:
            if aluno.ano_letivo.pk == convocao_enade.ano_letivo.pk and (
                convocao_enade.percentual_minimo_ingressantes <= percentual_ch_componentes_cumprido <= convocao_enade.percentual_maximo_ingressantes
            ):
                RegistroConvocacaoENADE.objects.create(
                    aluno=aluno,
                    convocacao_enade=convocao_enade,
                    percentual_ch_cumprida=percentual_ch_componentes_cumprido,
                    tipo_convocacao=RegistroConvocacaoENADE.TIPO_CONVOCACAO_INGRESSANTE,
                )
            elif convocao_enade.percentual_minimo_concluintes <= percentual_ch_componentes_cumprido <= convocao_enade.percentual_maximo_concluintes:
                RegistroConvocacaoENADE.objects.create(
                    aluno=aluno,
                    convocacao_enade=convocao_enade,
                    percentual_ch_cumprida=percentual_ch_componentes_cumprido,
                    tipo_convocacao=RegistroConvocacaoENADE.TIPO_CONVOCACAO_CONCLUINTE,
                )
    task.finalize('Lista de convocados atualizada com sucesso.', '/edu/convocacao_enade/{}/'.format(convocao_enade.pk))


@task('Exportar Alunos - XLS')
def exportar_listagem_alunos_xls(alunos, ano_letivo, periodo_letivo, filtros, campos_exibicao, cabecalhos, task=None):
    count = 0
    rows = [['#', 'Matrícula', 'Nome']]
    for campo in campos_exibicao:
        for label in cabecalhos:
            if label[0] == campo:
                rows[0].append(format_(label[1], html=False))
    task.count(alunos, alunos)
    for aluno in task.iterate(alunos):
        if ano_letivo and periodo_letivo:
            aluno.ano_letivo_referencia = ano_letivo
            aluno.periodo_letivo_referencia = periodo_letivo
        count += 1
        row = [count, format_(aluno.matricula, html=False), format_(aluno.get_nome_social_composto(), html=False)]
        for campo in campos_exibicao:
            row.append(format_(getattrr(aluno, campo), html=False))
        rows.append(row)
    rows_filtros = [['FILTROS']]
    for filtro in filtros:
        rows_filtros.append([filtro.get('chave'), filtro.get('valor')])
    if len(rows) >= 65536:
        CsvResponse(rows, processo=task)
    else:
        XlsResponse({'Registros': rows, 'Filtros': rows_filtros}, processo=task)


@task('Auditoria Censos')
def exportar_auditoria_censos(tipo, uo, curso, nivel_ensino, modalidade, situacao, cpf_operador, task=None):
    rows = []
    qs = Aluno.objects.all()
    if uo:
        qs = qs.filter(curso_campus__diretoria__setor__uo=uo)
    if curso:
        qs = qs.filter(curso_campus=curso)
    if nivel_ensino:
        qs = qs.filter(curso_campus__modalidade__nivel_ensino__in=nivel_ensino)
    if modalidade:
        qs = qs.filter(curso_campus__modalidade__in=modalidade)
    if situacao:
        qs = qs.filter(situacao__in=situacao)

    if tipo == 1:  # Dados Divergentes com a Receita Federal
        rows.append(['Auditoria', 'CPF', 'Matrícula', 'Nome SUAP', 'Nome RF', 'Nascimento SUAP', 'Nascimento RF', 'Mãe SUAP', 'Mãe RF'])
        for aluno in task.iterate(qs):
            dados_rf = aluno.get_dados_receita_federal(cpf_operador)
            if dados_rf:
                row = [
                    'Dados Divergentes com a Receita Federal',
                    format_(aluno.pessoa_fisica.cpf),
                    format_(aluno.matricula),
                ]
                if aluno.pessoa_fisica.nome_registro != dados_rf['Nome']:
                    row.append(aluno.pessoa_fisica.nome_registro)
                    row.append(dados_rf['Nome'])
                else:
                    row.append('-')
                    row.append('-')
                nascimento_suap = re.sub(r'\D', '', str(aluno.pessoa_fisica.nascimento_data))
                nascimento_rf = re.sub(r'\D', '', str(dados_rf['DataNascimento']))
                if nascimento_suap != nascimento_rf:
                    row.append(f'{nascimento_suap[6:8]}/{nascimento_suap[4:6]}/{nascimento_suap[0:4]}')
                    row.append(f'{nascimento_rf[6:8]}/{nascimento_rf[4:6]}/{nascimento_rf[0:4]}')
                else:
                    row.append('-')
                    row.append('-')
                if aluno.nome_mae != dados_rf['NomeMae']:
                    row.append(aluno.nome_mae)
                    row.append(dados_rf['NomeMae'])
                else:
                    row.append('-')
                    row.append('-')
                rows.append(row)

    elif tipo == 2:  # Matrículas na mesma Modalidade
        rows.append(['Auditoria', 'CPF', 'Matrícula', 'Nome', 'Modalidade', 'Situação', 'Curso'])
        qs = qs.values('curso_campus__modalidade', 'pessoa_fisica__cpf').annotate(count=Count('curso_campus__modalidade'))
        for q in task.iterate(qs):
            if q['count'] > 1:
                alunos = Aluno.objects.filter(situacao__in=situacao, pessoa_fisica__cpf=q['pessoa_fisica__cpf'], curso_campus__modalidade_id=q['curso_campus__modalidade']).values('matricula', 'pessoa_fisica__cpf', 'pessoa_fisica__nome_registro', 'curso_campus__modalidade__descricao', 'situacao__descricao', 'curso_campus__descricao')
                for aluno in alunos:
                    row = [
                        'Matrículas na mesma Modalidade',
                        format_(aluno['pessoa_fisica__cpf']),
                        format_(aluno['matricula']),
                        format_(aluno['pessoa_fisica__nome_registro']),
                        format_(aluno['curso_campus__modalidade__descricao']),
                        format_(aluno['situacao__descricao']),
                        format_(aluno['curso_campus__descricao']),
                    ]
                    rows.append(row)
    else:  # Nome com Pontuação/Caracter Especial
        rows.append(['Auditoria', 'CPF', 'Matrícula', 'Nome', 'Campus', 'Diretoria', 'Curso'])
        for aluno in task.iterate(qs):
            nome = aluno.pessoa_fisica.nome_registro
            if re.search(r'\W', nome.replace(' ', '')):
                row = [
                    'Nome com Pontuação/Caracter Especial',
                    format_(aluno.pessoa_fisica.cpf),
                    format_(aluno.matricula),
                    format_(nome),
                    format_(aluno.curso_campus.diretoria.setor.uo),
                    format_(aluno.curso_campus.diretoria),
                    format_(aluno.curso_campus),
                ]
                rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Atualizar Código do Aluno - EDUCACENSO')
def atualizar_codigo_educacenso(registros, task=None):

    def _similaridade(a, b):
        tamanho = min(len(a), len(b))
        a = a[:tamanho]
        b = b[:tamanho]
        return similaridade(a, b)

    lista = []
    c = 0
    for line in task.iterate(registros):
        c += 1
        tokens = line.decode().split('|')
        matricula = tokens[0]
        cpf = mask_cpf(tokens[1].strip())
        codigo_educacenso = tokens[-1].strip()
        qs = Aluno.objects.filter(matricula=matricula, pessoa_fisica__cpf=cpf)
        if qs.exists():
            Aluno.objects.filter(matricula=matricula).update(codigo_educacenso=codigo_educacenso)
        else:
            nascimento_data = datetime.datetime.strptime(tokens[4], "%d/%m/%Y")
            qs = Aluno.objects.filter(matricula=matricula, pessoa_fisica__nascimento_data=nascimento_data)
            if qs.exists():
                aluno = qs[0]
                nome_mae = tokens[5].strip()
                nome_pai = tokens[6].strip()
                nome_mae1 = to_ascii(aluno.nome_mae or aluno.pessoa_fisica.nome_mae or '').upper().replace('.', '').replace('\'', '').replace('-', '').strip()
                nome_pai1 = to_ascii(aluno.nome_pai or aluno.pessoa_fisica.nome_pai or '').upper().replace('.', '').replace('\'', '').replace('-', '').strip()
                if nome_mae == nome_mae1:
                    Aluno.objects.filter(matricula=matricula).update(codigo_educacenso=codigo_educacenso)
                else:
                    similaridade_nome_mae = _similaridade(nome_mae, nome_mae1)
                    similaridade_nome_pai = nome_pai and nome_pai1 and _similaridade(nome_pai, nome_pai1) or 0
                    if similaridade_nome_mae > 0.8 or (similaridade_nome_mae > 0.5 and similaridade_nome_pai > 0.7):
                        Aluno.objects.filter(matricula=matricula).update(codigo_educacenso=codigo_educacenso)
                    else:
                        lista.append(
                            '{}|{}|{}|{}|{}|{}|{}|{}|{}|{}'.format(
                                matricula,
                                aluno.pessoa_fisica.nome,
                                tokens[5],
                                codigo_educacenso,
                                nome_mae,
                                nome_mae1,
                                similaridade_nome_mae,
                                nome_pai,
                                nome_pai1,
                                similaridade_nome_pai,
                            )
                        )
            else:
                pass  # l.append(u'{}|{}|{}|{}|{}|{}|{}|{}|{}|{}'.format(matricula, nome, tokens[2], codigo_educacenso, nome_mae, '', '', nome_pai, '', ''))
    if lista:
        output = tempfile.NamedTemporaryFile(mode='w', dir=os.path.join(settings.TEMP_DIR), delete=False, suffix='.txt')
        output.write('\r\n'.join(lista))
        output.close()
        task.finalize('Processamento realizado parcialmente. Gerado arquivo de registros não econtrados', '/edu/atualizar_codigo_educacenso/', file_path=output.name)
    else:
        task.finalize('Processamento realizado com sucesso', '/edu/atualizar_codigo_educacenso/')


@task('Exportar Dados - CENSUP')
def exportar_dados_censup(tipo, ano, uos, amostra, cpfs, ignorar_cpfs, task=None):
    censup.Exportador(tipo, ano, uos=uos, amostra=amostra, cpfs=cpfs, ignorar_cpfs=ignorar_cpfs, task=task)


@task('Exportar Dados - EDUCACENSO (Primeira Etapa)')
def exportar_dados_educacenso(ano, uo, ignorar_erros, task=None):
    educacenso.Exportador(ano, uo, ignorar_erros, task=task)


@task('Exportar Dados - EDUCACENSO (Segunda Etapa)')
def exportar_dados_educacenso2(ano, uo, ignorar_erros, task=None):
    educacenso.ExportadorEtapa2(ano, uo, ignorar_erros, task=task)


@task('Importar Dados - EDUCACENSO (Segunda Etapa)')
def importar_dados_educacenso2(ano_letivo, conteudo, task=None):
    matriculas_periodo = {}
    lines = conteudo.split('\n')
    for line in task.iterate(lines):
        line = line.strip()
        if line.startswith('30|'):
            line30 = line.split('|')
            codigo_educacenso = line30[3]
            matricula = line30[2]
            nis = line30[38]
            qs = Aluno.objects.filter(matricula=matricula)
            if qs.exists():
                qs.update(codigo_educacenso=codigo_educacenso, nis=nis)
                matricula_periodo = MatriculaPeriodo.objects.filter(
                    aluno__matricula=matricula, ano_letivo=ano_letivo, periodo_letivo=1
                ).first()
                matriculas_periodo[codigo_educacenso] = matricula_periodo
            else:
                cpf = line30[4]
                if cpf.strip():
                    cpf = mask_cpf(cpf)
                codigo_educacenso_campus = line30[1]
                qs_matricula_periodo = MatriculaPeriodo.objects.filter(
                    aluno__pessoa_fisica__cpf=cpf,
                    aluno__curso_campus__diretoria__setor__uo__codigo_inep=codigo_educacenso_campus,
                    aluno__curso_campus__modalidade__in=(
                        Modalidade.INTEGRADO,
                        Modalidade.INTEGRADO_EJA,
                        Modalidade.SUBSEQUENTE,
                        Modalidade.CONCOMITANTE,
                        Modalidade.PROEJA_FIC_FUNDAMENTAL,
                    ),
                    ano_letivo=ano_letivo,
                    periodo_letivo=1,
                )
                if qs_matricula_periodo.count() == 1:
                    matricula_periodo = qs_matricula_periodo.first()
                    Aluno.objects.filter(pk=matricula_periodo.aluno_id).update(codigo_educacenso=codigo_educacenso,
                                                                               nis=nis)
                    matriculas_periodo[codigo_educacenso] = matricula_periodo
                else:
                    continue
        if line.startswith('60|'):
            line60 = line.split('|')
            codigo_educacenso = line60[3]
            codigo_educacenso_periodo = line60[6]
            codigo_educacenso_turma = line60[5]
            matricula_periodo = matriculas_periodo.get(codigo_educacenso)
            if matricula_periodo:
                matricula_periodo.codigo_educacenso = codigo_educacenso_periodo
                matricula_periodo.save()
                if matricula_periodo.turma_id:  # and not matricula_periodo.turma.codigo_educacenso
                    matricula_periodo.turma.codigo_educacenso = codigo_educacenso_turma
                    matricula_periodo.turma.save()
    task.finalize('Arquivo processado com sucesso.', '..')


@task('Exportar Alunos sem Código - EDUCACENSO')
def exportar_alunos_sem_codigo_educacenso(ano, task=None):
    educacenso.ExportadorAlunosSemCodigo(ano, task=task)


@task('Processar Pedidos de Matrícula')
def processar_pedidos_matricula(self, task=None):
    pedidos_matricula_por_ira = self.pedidomatricula_set.filter(pedidomatriculadiario__isnull=False, turma__isnull=False).distinct().order_by('-matricula_periodo__aluno__ira')
    diarios_pedidos_pendentes = Diario.objects.filter(
        pedidomatriculadiario__pedido_matricula__configuracao_pedido_matricula=self, pedidomatriculadiario__data_processamento__isnull=True
    ).distinct()
    pedidos_matricula_vinculo = self.pedidomatricula_set.exclude(matricula_periodo__matriculadiario__isnull=False)

    task.count(pedidos_matricula_por_ira, diarios_pedidos_pendentes, pedidos_matricula_vinculo)

    def do():
        try:
            sid = transaction.savepoint()
            # APENAS SERIADO
            # percorrendo os pedidos que possuem turma e pedidos de diários ordenados pelo ira e inserindo na turma e nos diários dela os alunos que não mudaram de turma
            pedidos_mudanca_turma = []
            for pedido_matricula in task.iterate(pedidos_matricula_por_ira):
                ultima_turma_cursada = pedido_matricula.matricula_periodo.aluno.get_ultima_turma_cursada()
                turma_solicitada = pedido_matricula.turma
                pedidos_matricula_diario_turma = pedido_matricula.pedidomatriculadiario_set.filter(diario__turma=turma_solicitada)
                matricular = False
                if ultima_turma_cursada:
                    if pedido_matricula.matricula_periodo.aluno.situacao.pk not in [
                        SituacaoMatricula.MATRICULADO,
                        SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL,
                        SituacaoMatricula.TRANCADO,
                        SituacaoMatricula.INTERCAMBIO,
                        SituacaoMatricula.TRANCADO_VOLUNTARIAMENTE,
                    ]:
                        pedidos_matricula_diario_turma.update(deferido=False, motivo=PedidoMatriculaDiario.MOTIVO_MATRICULA_INATIVA, data_processamento=datetime.date.today())

                    elif ultima_turma_cursada.sequencial == turma_solicitada.sequencial:
                        # mesma_turma
                        matricular = True
                    else:
                        # mudanca_turma
                        pedidos_mudanca_turma.append(pedido_matricula)
                else:
                    # TODO ANALISAR
                    # alunos integralizados do Q-Acadêmico sem turma na última matrícula período
                    if pedido_matricula.matricula_periodo.situacao.pk not in [
                        SituacaoMatriculaPeriodo.MATRICULADO,
                        SituacaoMatriculaPeriodo.EM_ABERTO,
                        SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL,
                    ]:
                        pedidos_matricula_diario_turma.update(deferido=False, motivo=PedidoMatriculaDiario.MOTIVO_MATRICULA_INATIVA, data_processamento=datetime.date.today())
                    elif turma_solicitada.get_alunos_matriculados().count() < turma_solicitada.quantidade_vagas:
                        matricular = True
                    else:
                        # indeferindo devido ao ira
                        pedidos_matricula_diario_turma.update(deferido=False, motivo=PedidoMatriculaDiario.MOTIVO_IRA, data_processamento=datetime.date.today())

                if matricular:
                    # matriculando na turma
                    pedido_matricula.matricular_na_turma()

                    # matriculando nos diários da turma acima
                    for pedido_matricula_diario in pedidos_matricula_diario_turma:
                        pedido_matricula_diario.matricular_no_diario(PedidoMatriculaDiario.MOTIVO_PERIODIZADO)

            # verificando se os alunos que solicitaram mudança de turma terão direito a vaga
            for pedido_matricula in pedidos_mudanca_turma:
                turma_solicitada = pedido_matricula.turma
                pedidos_matricula_diario_turma_solicitada = pedido_matricula.pedidomatriculadiario_set.filter(diario__turma=turma_solicitada)

                if pedido_matricula.matricula_periodo.situacao.pk not in [
                    SituacaoMatriculaPeriodo.MATRICULADO,
                    SituacaoMatriculaPeriodo.EM_ABERTO,
                    SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL,
                ]:
                    pedidos_matricula_diario_turma_solicitada.update(
                        deferido=False, motivo=PedidoMatriculaDiario.MOTIVO_MATRICULA_INATIVA, data_processamento=datetime.date.today()
                    )
                elif turma_solicitada.get_alunos_matriculados().count() < turma_solicitada.quantidade_vagas:
                    # matriculando na turma
                    pedido_matricula.matricular_na_turma()

                    # matriculando nos diários
                    for pedido_matricula_diario in pedidos_matricula_diario_turma_solicitada:
                        pedido_matricula_diario.matricular_no_diario(PedidoMatriculaDiario.MOTIVO_IRA)
                else:
                    # indeferindo mudança de turma
                    pedidos_matricula_diario_turma_solicitada.update(deferido=False, motivo=PedidoMatriculaDiario.MOTIVO_IRA, data_processamento=datetime.date.today())

            # APENAS SERIADO

            # CRÉDITO E DEPÊNDENCIAS DO SERIADO
            # obtendo os diarios com pedido pendentes
            for diario in task.iterate(diarios_pedidos_pendentes):
                # obtendo os pedidos pendentes deste diario e adicionando o atributo prioridade_periodo
                pedidos_pendentes = diario.pedidomatriculadiario_set.filter(pedido_matricula__configuracao_pedido_matricula=self, data_processamento__isnull=True)
                pedidos_prioridade_periodo = []
                for pedido in pedidos_pendentes:
                    # tratando prioridade para optativos
                    prioridade_periodo = 1
                    if not pedido.diario.componente_curricular.optativo:
                        prioridade_periodo = abs(pedido.pedido_matricula.matricula_periodo.aluno.periodo_atual - pedido.diario.componente_curricular.periodo_letivo)

                    pedido.prioridade_periodo = prioridade_periodo
                    pedido.ira = pedido.pedido_matricula.matricula_periodo.aluno.ira
                    pedidos_prioridade_periodo.append(pedido)

                # ordenando a lista pedidos_prioridade por prioridade_periodo, -ira
                pedidos_prioridade_periodo = sorted(pedidos_prioridade_periodo, key=operator.attrgetter('prioridade_periodo'))
                pedidos_prioridade_periodo = sorted(pedidos_prioridade_periodo, key=operator.attrgetter('ira'), reverse=True)

                # percorrendo lista ordenada para deferimento e indeferimento
                for pedido_matricula_diario in pedidos_prioridade_periodo:
                    # aluno do pedido esta no mesmo periodo do componente curricular
                    motivo = PedidoMatriculaDiario.MOTIVO_PERIODO_IRA
                    if pedido_matricula_diario.prioridade_periodo == 0:
                        motivo = PedidoMatriculaDiario.MOTIVO_PERIODIZADO

                    if pedido_matricula_diario.pedido_matricula.matricula_periodo.situacao.pk not in [
                        SituacaoMatriculaPeriodo.MATRICULADO,
                        SituacaoMatriculaPeriodo.EM_ABERTO,
                        SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL,
                    ]:
                        pedido_matricula_diario.indeferir(PedidoMatriculaDiario.MOTIVO_MATRICULA_INATIVA)
                    elif pedido_matricula_diario.diario.matriculadiario_set.all().count() < pedido_matricula_diario.diario.quantidade_vagas:
                        # matriculando no diário
                        pedido_matricula_diario.matricular_no_diario(motivo)
                    else:
                        # indeferindo
                        pedido_matricula_diario.indeferir(motivo)

            # CRÉDITO E DEPÊNDENCIAS DO SERIADO
            # alunos que realizaram pedidos de matrícula e que não houve deferimento em nenhum diário
            pedidos_matricula_vinculo = self.pedidomatricula_set.exclude(matricula_periodo__matriculadiario__isnull=False)
            for pedido_matricula_vinculo in task.iterate(pedidos_matricula_vinculo):
                if pedido_matricula_vinculo.matricula_periodo.situacao.pk in [
                    SituacaoMatriculaPeriodo.MATRICULADO,
                    SituacaoMatriculaPeriodo.EM_ABERTO,
                    SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL,
                ]:
                    pedido_matricula_vinculo.matricula_periodo.matricula_vinculo()

            ids_matriculas_diarios_cancelados = self.pedidomatricula_set.filter(
                matriculas_diario_canceladas__situacao=MatriculaDiario.SITUACAO_CURSANDO
            ).values_list('matriculas_diario_canceladas', flat=True)
            for matricula_diario in MatriculaDiario.objects.filter(id__in=ids_matriculas_diarios_cancelados):
                try:
                    matricula_diario.cancelar()
                except ValidationError as e:
                    print(e, 9999999)
                    pass
            transaction.savepoint_commit(sid)
            task.finalize('Pedidos de matrícula processados com sucesso.', '/edu/configuracao_pedido_matricula/{}/?tab=monitoramento'.format(self.pk))
        except Exception as e:
            transaction.savepoint_rollback(sid)
            raise e

    do()


@task('Auditoria SISTEC -> SUAP')
def exportar_sistec_suap(planilha_path, campus, task=None):
    retry = 0
    while not os.path.exists(planilha_path) and retry < 60:
        sleep(2)
        retry += 1

    planilha = open(planilha_path, encoding="iso-8859-1")
    rsheet = list(csv.DictReader(planilha, delimiter=";"))

    Task.objects.filter(pk=task.pk).update(total=len(rsheet))

    wworkbook = xlwt.Workbook(encoding='utf-8')
    wsheet = wworkbook.add_sheet('Alunos')
    coluna_insercao = 0
    row = 0
    fields = None

    for data in task.iterate(rsheet):
        row += 1
        try:
            if fields is None:
                fields = data.keys()
                coluna_insercao = 0
                for key in fields:
                    wsheet.write(0, coluna_insercao, key)
                    coluna_insercao += 1

                wsheet.write(0, coluna_insercao, 'SITUACAO_NO_SISTEC')
                wsheet.write(0, coluna_insercao + 1, 'SITUACAO_NO_SUAP')
                wsheet.write(0, coluna_insercao + 2, 'COMPARACAO')
                wsheet.write(0, coluna_insercao + 3, 'DIRETORIA')

            for idx, key in enumerate(fields):
                wsheet.write(row, idx, data[key])

            coluna_busca = data['NO_STATUS_MATRICULA']
            coluna_cpf_aluno = data['NU_CPF']
            coluna_codigo_curso = int(data['CO_CURSO'])
            coluna_data_inicio = data['DT_DATA_INICIO']

            campo = coluna_busca
            codigo_curso = int(coluna_codigo_curso)
            codigo_unidade = campus.codigo_sistec

            # tratando data caso venha no formato dd/mm/yyyy ou yyyy-mm-dd
            if '/' in coluna_data_inicio:
                day, month, year = list(map(int, coluna_data_inicio.split(' ')[0].split('/')))
            else:
                year, month, day = list(map(int, coluna_data_inicio.split(' ')[0].split('-')))

            data_inicio = datetime.datetime(year, month, day)

            # Tratando o CPF - Se CPF vier mascarado retira a máscara e aplica novamente
            cpf_aluno = str(coluna_cpf_aluno).replace('.', '').replace('-', '')
            cpf_aluno = str(int(cpf_aluno))
            cpf_aluno = cpf_aluno.rjust(11, '0')
            cpf_aluno = mask_cpf(cpf_aluno)
            wsheet.write(row, coluna_insercao, coluna_busca)

            qs_aluno = Aluno.objects.filter(pessoa_fisica__cpf=cpf_aluno, curso_campus__diretoria__setor__uo__codigo_sistec=codigo_unidade)
            qs_aluno = (
                qs_aluno.filter(curso_campus__codigo_sistec=codigo_curso)
                or qs_aluno.filter(curso_campus__codigo_sistec__contains=';{};'.format(codigo_curso))
                or qs_aluno.filter(curso_campus__codigo_sistec__startswith='{};'.format(codigo_curso))
                or qs_aluno.filter(curso_campus__codigo_sistec__endswith=';{}'.format(codigo_curso))
            )
            if qs_aluno.count() == 1:
                aluno = qs_aluno[0]
            else:
                aluno = qs_aluno.get(ano_letivo__ano=data_inicio.year)
            wsheet.write(row, coluna_insercao + 1, str(aluno.situacao).upper())

            # Calculando o valor do campo de comparação
            valor_campo_comparacao = ''
            if aluno.situacao.pk in [SituacaoMatricula.EVASAO, SituacaoMatricula.NAO_CONCLUIDO]:
                valor_campo_comparacao = ['ABANDONO', 'DESLIGADO']
            elif aluno.situacao.pk in [SituacaoMatricula.CONCLUIDO, SituacaoMatricula.FORMADO]:
                valor_campo_comparacao = ['CONCLUÍDA']
            elif aluno.situacao.pk in [
                SituacaoMatricula.CANCELADO,
                SituacaoMatricula.JUBILADO,
                SituacaoMatricula.CANCELAMENTO_COMPULSORIO,
                SituacaoMatricula.FALECIDO,
                SituacaoMatricula.CANCELAMENTO_POR_DUPLICIDADE,
                SituacaoMatricula.CANCELAMENTO_POR_DESLIGAMENTO,
            ]:
                valor_campo_comparacao = ['ABANDONO', 'DESLIGADO']
            elif aluno.situacao.pk in [
                SituacaoMatricula.MATRICULADO,
                SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL,
                SituacaoMatricula.INTERCAMBIO,
                SituacaoMatricula.TRANCADO_VOLUNTARIAMENTE,
                SituacaoMatricula.TRANCADO,
            ]:
                valor_campo_comparacao = ['EM_CURSO']
            elif aluno.situacao.pk in [
                SituacaoMatricula.CONCLUDENTE,
                SituacaoMatricula.ESTAGIARIO_CONCLUDENTE,
                SituacaoMatricula.AGUARDANDO_COLACAO_DE_GRAU,
                SituacaoMatricula.AGUARDANDO_ENADE,
            ]:
                valor_campo_comparacao = ['INTEGRALIZADA']
            elif aluno.situacao.pk in [SituacaoMatricula.TRANSFERIDO_EXTERNO]:
                valor_campo_comparacao = ['TRANSF_EXT']
            elif aluno.situacao.pk in [SituacaoMatricula.TRANSFERIDO_INTERNO]:
                qs = (
                    Aluno.objects.filter(pessoa_fisica__cpf=aluno.pessoa_fisica.cpf, curso_campus__modalidade=aluno.curso_campus.modalidade, ano_letivo__gte=aluno.ano_letivo)
                    .exclude(pk=aluno.pk)
                    .exclude(curso_campus__diretoria__setor__uo=aluno.curso_campus.diretoria.setor.uo)
                    .order_by('-ano_letivo__ano')
                )
                if qs.exists():
                    valor_campo_comparacao = ['TRANSF_EXT']
                else:
                    valor_campo_comparacao = ['TRANSF_INT']
            elif campo == 'REPROVADO':
                valor_campo_comparacao = ['MATRICULADO']

            if campo in valor_campo_comparacao:
                wsheet.write(row, coluna_insercao + 2, 'CONVERGENTE')
            else:
                wsheet.write(row, coluna_insercao + 2, 'DIVERGENTE')

            # Adicionando a Diretoria do aluno
            wsheet.write(row, coluna_insercao + 3, str(aluno.curso_campus.diretoria))

        except Aluno.DoesNotExist:
            wsheet.write(row, coluna_insercao + 1, 'NÃO LOCALIZADO')
            wsheet.write(row, coluna_insercao + 2, 'NÃO LOCALIZADO')
            wsheet.write(row, coluna_insercao + 3, 'NÃO LOCALIZADO')
        except Aluno.MultipleObjectsReturned:
            aluno = qs_aluno.first()
            wsheet.write(row, coluna_insercao + 1, 'VERIFICAR')
            wsheet.write(row, coluna_insercao + 2, 'VERIFICAR')
            wsheet.write(row, coluna_insercao + 3, str(aluno.curso_campus.diretoria))
        except Exception:
            pass

    planilha.close()

    response = tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.xls')
    wworkbook.save(response)
    response.close()
    task.finalize('Arquivo gerado com sucesso.', '..', file_path=response.name)


@task('Emitir Boletins em PDF')
def emitir_boletins_pdf(request, matriculas_periodo, task=None):
    from edu import views
    pdf = views.emitir_boletins_aluno_pdf(request, matriculas_periodo, task)
    tmp = tempfile.NamedTemporaryFile(suffix='.pdf', mode='w+b', delete=False)
    tmp.write(pdf.content)
    tmp.close()
    return task.finalize('Arquivo gerado com sucesso.', '..', file_path=tmp.name)


@task('Exportar Relatório EDUCACENSO para XLS')
def relatorio_educacenso_xls(alunos, ano_letivo, periodo_letivo, task=None):
    rows = [['#', 'Matrícula', 'Nome', 'CPF', 'Diretoria', 'Turma', 'Situação da Matrícula', 'Situação no Período', 'Rendimento', 'Movimento', 'Concluinte']]

    count = 0
    for aluno in task.iterate(alunos):
        qs = MatriculaPeriodo.objects.filter(aluno=aluno).order_by('-ano_letivo__ano', '-periodo_letivo')
        if periodo_letivo not in [None, '', '0', 0]:
            qs = qs.filter(periodo_letivo=periodo_letivo)
        if ano_letivo:
            qs = qs.filter(ano_letivo=ano_letivo)
        if qs:
            aluno.matricula_periodo = qs[0]
        count += 1
        if aluno.matricula_periodo.get_concluinte() is not None:
            if aluno.matricula_periodo.get_concluinte():
                concluinte = 'Sim'
            else:
                concluinte = 'Não'
        else:
            concluinte = '-'

        row = [
            count,
            format_(aluno.matricula),
            format_(aluno.get_nome_social_composto()),
            format_(aluno.pessoa_fisica.cpf),
            format_(aluno.curso_campus.diretoria),
            format_(aluno.matricula_periodo.get_codigo_turma()),
            format_(aluno.situacao),
            format_(aluno.matricula_periodo.situacao),
            format_(aluno.matricula_periodo.get_rendimento()),
            format_(aluno.matricula_periodo.get_movimento()),
            concluinte,
        ]
        rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Relatório CENSUP para XLS')
def relatorio_censup_xls(alunos, ano_letivo, periodo_letivo, task=None):
    rows = [
        [
            '#',
            'Matrícula',
            'Nome',
            'CPF',
            'Curso',
            'Situação da Matrícula',
            'Situação no Período',
            'Situação Vínculo Curso',
            'Turno',
            'Reserva de Vagas',
            'Apoio Social',
            'Atividade Extracurricular',
            'C.H. Curso',
            'C.H. Cumprida',
        ]
    ]
    count = 0
    for aluno in task.iterate(alunos):
        count += 1
        qs = MatriculaPeriodo.objects.filter(aluno=aluno).order_by('-ano_letivo__ano', '-periodo_letivo')
        if periodo_letivo not in [None, '', '0', 0]:
            qs = qs.filter(periodo_letivo=periodo_letivo)
        if ano_letivo:
            qs = qs.filter(ano_letivo=ano_letivo)
        if qs:
            aluno.matricula_periodo = qs[0]
        row = [
            count,
            format_(aluno.matricula),
            format_(aluno.get_nome_social_composto()),
            format_(aluno.pessoa_fisica.cpf),
            format_(aluno.curso_campus),
            format_(aluno.situacao),
            format_(aluno.matricula_periodo.situacao),
            format_(aluno.matricula_periodo.get_situacao_censup()),
            format_(aluno.turno),
            (aluno.tem_cota() or 'Não'),
            (aluno.tem_apoio_social() and format_(aluno.tem_apoio_social()) or 'Não'),
            (aluno.tem_atividade_extracurricular() and format_(aluno.tem_atividade_extracurricular()) or 'Não'),
            format_(aluno.matriz and aluno.matriz.get_carga_horaria_total_prevista() or '-'),
            format_(aluno.get_ch_componentes_cumpridos()),
        ]
        rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Relatório de Aluno por Disciplina Pendente para XLS')
def relatorio_pordisciplinapendente_xls(alunos, task=None):
    rows = [['#', 'Matrícula', 'Nome', 'Sigla', 'Período', 'Descrição', 'Tipo']]
    count = 0
    for aluno in task.iterate(alunos):
        for componente_pendente in aluno.get_componentes_obrigatorios_pendentes(True):
            count += 1
            row = [
                count,
                format_(aluno.matricula),
                format_(aluno.get_nome_social_composto()),
                format_(componente_pendente.componente.sigla),
                format_(componente_pendente.periodo_letivo),
                format_(componente_pendente.componente.descricao_historico),
                format_(componente_pendente.get_tipo_display()),
            ]
            rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Relatório de Aluno por Disciplina Cursando para XLS')
def relatorio_pordisciplinacursando_xls(alunos, task=None):
    rows = [['#', 'Matrícula', 'Nome', 'Sigla', 'Período', 'Descrição', 'Tipo', 'Diario', 'Situação']]
    count = 0
    for aluno in task.iterate(alunos):
        for md in aluno.get_matriculas_diario_cursando():
            count += 1
            row = [
                count,
                format_(aluno.matricula),
                format_(aluno.get_nome_social_composto()),
                format_(md.diario.componente_curricular.componente.sigla),
                format_(md.diario.componente_curricular.periodo_letivo),
                format_(md.diario.componente_curricular.componente.descricao_historico),
                format_(md.diario.componente_curricular.get_tipo_display()),
                format_(md.diario.id),
                format_(md.get_situacao_diario()['rotulo']),
            ]
            rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Relatório de Aluno por TCC para XLS')
def relatorio_tcc_xls(alunos, task=None):
    rows = [['#', 'Matrícula', 'Aluno', 'Nível de Ensino', 'Tipo', 'Título', 'Banca', 'Data da Defesa', 'Nota', 'Situação']]
    i = 0
    for aluno in task.iterate(alunos):
        i += 1
        for projeto_final in aluno.get_projetos_finais():
            rows.append(
                [
                    i,
                    aluno.matricula,
                    aluno.pessoa_fisica.nome,
                    aluno.curso_campus.modalidade.nivel_ensino.descricao,
                    projeto_final.tipo,
                    projeto_final.titulo,
                    ', '.join(
                        [
                            'Presidente:',
                            str(projeto_final.presidente),
                            'Examinador:',
                            str(projeto_final.examinador_interno),
                            'Examinador:',
                            str(projeto_final.examinador_externo),
                        ]
                    ),
                    format_(projeto_final.data_defesa),
                    format_(projeto_final.nota),
                    projeto_final.get_situacao_display(),
                ]
            )
    return XlsResponse(rows, processo=task)


@task('Exportar Listagem de Professores para XLS')
def exportar_listagem_professores_xls(professores, campos_exibicao, choices, task=None):
    rows = [['#', 'Matrícula', 'Nome']]
    for campo in campos_exibicao:
        for label in choices:
            if label[0] == campo:
                rows[0].append(format_(label[1]))

    count = 0
    for professor in task.iterate(professores):
        count += 1
        row = [count, format_(professor.get_matricula()), format_(professor.vinculo.pessoa.nome)]
        for campo in campos_exibicao:
            row.append(format_(getattrr(professor, campo), False))
        rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Relatório de Dependência para XLS')
def exportar_relatorio_dependencia_xls(matriculas_diarios, task=None):
    rows = [['#', 'Matrícula', 'Nome', 'Diário', 'Componente', 'Situação']]

    count = 0
    for matricula_diario in task.iterate(matriculas_diarios):
        count += 1
        diario = hasattr(matricula_diario, 'diario') and matricula_diario.diario.pk or matricula_diario.codigo_diario_pauta
        componente = (
            hasattr(matricula_diario, 'diario')
            and matricula_diario.diario.componente_curricular.componente.descricao_historico
            or matricula_diario.equivalencia_componente.componente.descricao_historico
        )
        row = [
            count,
            format_(matricula_diario.matricula_periodo.aluno.matricula),
            format_(matricula_diario.matricula_periodo.aluno.get_nome_social_composto()),
            format_(diario),
            format_(componente),
            format_(matricula_diario.matricula_periodo.situacao.descricao),
        ]
        rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Relatório de Diários para XLS')
def exportar_relatorio_diario_xls(diarios, campos_exibicao, choices, task=None):
    rows = [
        [
            '#',
            'Diário',
            ' Sigla do Componente',
            'Descrição do Componente',
            'Nível de Ensino',
            'Professores',
            'Carga-Horária Prevista dos Professores'
            'Posse Etapa 1',
            'Posse Etapa 2',
            'Posse Etapa 3',
            'Posse Etapa 4',
            'Posse Etapa Final',
        ]
    ]
    for campo in campos_exibicao:
        for label in choices:
            if label[0] == campo:
                if label[0] == 'turma.curso_campus':
                    rows[0].append('Código do Curso')
                    rows[0].append('Descrição do Curso')
                else:
                    rows[0].append(format_(label[1]))
    count = 0
    for diario in task.iterate(diarios):
        posse_etapa_2 = '-'
        posse_etapa_3 = '-'
        posse_etapa_4 = '-'
        if diario.componente_curricular.qtd_avaliacoes > 1:
            posse_etapa_2 = diario.get_posse_etapa_2_display()
        if diario.componente_curricular.qtd_avaliacoes > 2:
            posse_etapa_3 = diario.get_posse_etapa_3_display()
        if diario.componente_curricular.qtd_avaliacoes > 3:
            posse_etapa_4 = diario.get_posse_etapa_4_display()
        count += 1
        row = [
            count,
            format_(diario.id),
            format_(diario.componente_curricular.componente.sigla),
            format_(diario.componente_curricular.componente.descricao),
            format_(diario.componente_curricular.componente.nivel_ensino),
            ', '.join([str(x) for x in diario.get_professores_display()]),
            diario.get_resumo_ch_prevista(),
            format_(diario.get_posse_etapa_1_display()),
            format_(posse_etapa_2),
            format_(posse_etapa_3),
            format_(posse_etapa_4),
            format_(diario.get_posse_etapa_5_display()),
        ]
        for campo in campos_exibicao:
            if campo == 'turma.curso_campus':
                row.append(format_(diario.turma.curso_campus.codigo))
                row.append(format_(diario.turma.curso_campus.descricao))
            else:
                row.append(format_(getattrr(diario, campo)))
        rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Relatório de Diários para PDF')
def relatorio_diario_pdf(request, diarios, task=None):
    import zipfile
    from edu import views
    etapa = request.GET.get('etapa') or 1
    f = zipfile.ZipFile('{}{}.zip'.format(tempfile.mktemp(), datetime.datetime.now()), 'w')
    for diario in task.iterate(diarios):
        arquivo = views.diario_pdf(request, diario.pk, etapa)
        f.writestr('diario_{}.pdf'.format(diario.pk), arquivo.content)
    f.close()
    task.finalize('Arquivo gerado com sucesso.', '..', file_path=f.filename)


@task('Exportar Alunos Evadidos para XLS')
def exportar_evasao_em_lote_xls(alunos, task=None):
    count = 0
    rows = [['#', 'Matrícula', 'Aluno', 'Situação do Aluno', 'Situação da Matricula Período', 'Curso', 'Diretoria', 'Campus']]
    for aluno in task.iterate(alunos):
        count += 1
        row = [
            count,
            format_(aluno.matricula),
            format_(aluno.get_nome_social_composto()),
            format_(aluno.situacao),
            format_(aluno.get_ultima_matricula_periodo().situacao),
            format_(aluno.curso_campus.descricao),
            format_(aluno.curso_campus.diretoria),
            format_(aluno.curso_campus.diretoria.setor.uo),
        ]
        rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Estatísticas para XLS')
def exportar_estaticas_xls(alunos, task=None):
    rows = [['#', 'Matrícula', 'Aluno', 'Curso', 'Diretoria', 'Modalidade']]
    count = 0
    for aluno in task.iterate(alunos):
        count += 1
        row = [
            count,
            format_(aluno.matricula),
            format_(aluno.get_nome_social_composto()),
            format_(aluno.curso_campus),
            format_(aluno.curso_campus.diretoria),
            format_(aluno.curso_campus.modalidade),
        ]
        rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Indicadores para XLS')
def exportar_indicadores_xls(cursos, anos, modalidades, uos, tipos_necessidade_especial, tipos_transtorno, superdotacao, task=None):
    from edu.forms import IndicadoresForm
    rows = [
        [
            '#',
            'CURSO',
            'CURSO_NOME',
            'ANO',
            'MATRICULAS ATENDIDAS',
            'CONCLUIDOS',
            'RETIDOS',
            'MATRÍCULAS FINALIZADAS EVADIDAS',
            'REPROVADOS',
            'MATRICULAS CONTINUADAS REGULARES',
            'MATRÍCULAS CONTINUADAS RETIDAS',
            'CONCLUÍDOS NO PRAZO',
            'PREVISTO',
            'MATRÍCULAS FINALIZADAS',
            'CONCLUINTES',
            'INGRESSOS',
            '01 - Taxa de Retenção',
            '02 - Taxa de Conclusão',
            '03 - Taxa de Evasão',
            '04 - Taxa de Reprovações',
            '05 - Taxa de Matrícula Ativa Regular',
            '06 - Taxa de Matrícula Ativa Retida',
            '07 - Índice de Efetividade Acadêmica',
            '08 - Taxa de Saída com Êxito',
            '09 - Taxa de Permanência e Êxito',
            '10 - Índice de Eficácia',
        ]
    ]
    contador = 0
    for curso in task.iterate(cursos):
        variaveis = IndicadoresForm.processar_variaveis(
            anos[0],
            anos[-1],
            modalidades,
            uos,
            curso_id=curso,
            tipos_necessidade_especial=tipos_necessidade_especial,
            tipos_transtorno=tipos_transtorno,
            superdotacao=superdotacao,
        )
        indicadores = IndicadoresForm.gerar_indicadores(anos, variaveis)
        for ano in anos:
            contador += 1
            row = [
                contador,
                curso.codigo,
                curso.descricao_historico,
                ano,
                variaveis['ATENDIDOS'][ano].count(),
                variaveis['CONCLUIDOS'][ano].count(),
                variaveis['RETIDOS'][ano].count(),
                variaveis['EVADIDOS'][ano].count(),
                variaveis['REPROVADOS'][ano].count(),
                variaveis['CONTINUADOS_REGULARES'][ano].count(),
                variaveis['CONTINUADOS_RETIDOS'][ano].count(),
                variaveis['CONCLUIDOS_PRAZO'][ano].count(),
                variaveis['PREVISTOS'][ano].count(),
                variaveis['FINALIZADOS'][ano].count(),
                variaveis['CONCLUINTES'][ano].count(),
                variaveis['INGRESSOS'][ano].count(),
                format_(indicadores['01_TAXA_RETENCAO'][ano]),
                format_(indicadores['02_TAXA_CONCLUSAO'][ano]),
                format_(indicadores['03_TAXA_EVASAO'][ano]),
                format_(indicadores['04_TAXA_REPROVACOES'][ano]),
                format_(indicadores['05_TAXA_ATIVOS_REGULARES'][ano]),
                format_(indicadores['06_TAXA_ATIVOS_RETIDOS'][ano]),
                format_(indicadores['07_TAXA_EFETIVIDADE'][ano]),
                format_(indicadores['08_TAXA_SAIDA_EXITO'][ano]),
                format_(indicadores['09_TAXA_PERMANENCIA_EXITO'][ano]),
                format_(indicadores['10_INDICE_EFICACIA'][ano]),
            ]
            rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Relatório do CENSUP para XLS')
def exportar_relatorio_censup_xls(file_contents, tipo_relatorio, coluna_busca, coluna_salva, task=None):
    from edu.forms import PreencherRelatorioCensupForm
    rworkbook = xlrd.open_workbook(file_contents=file_contents, formatting_info=True)
    rsheet = rworkbook.sheet_by_index(0)
    wworkbook = copy(rworkbook)
    wsheet = wworkbook.get_sheet(0)
    for row in task.iterate(list(range(0, rsheet.nrows))):
        try:
            campo = rsheet.cell_value(row, coluna_busca)
            if tipo_relatorio == PreencherRelatorioCensupForm.CAMPUS_CURSO:
                qs = CursoCampus.objects.filter(codigo_censup=campo).select_related('diretoria', 'diretoria__setor').values_list('diretoria__setor__sigla', flat=True)
            else:
                if type(campo) == float:
                    campo = str(campo)[0:-2]
                if len(campo.strip()) < 11:
                    campo = campo.strip().zfill(11)
                cpf = '{}.{}.{}-{}'.format(campo[0:3], campo[3:6], campo[6:9], campo[9:11])
                if tipo_relatorio == PreencherRelatorioCensupForm.CAMPUS_PROFESSOR:
                    qs = (
                        Professor.objects.filter(vinculo__pessoa__pessoafisica__cpf=cpf)
                        .select_related('vinculo__pessoa', 'vinculo__setor')
                        .values_list('vinculo__setor__sigla', flat=True)
                    )
                else:
                    qs = Aluno.objects.filter(pessoa_fisica__cpf=cpf, curso_campus__modalidade__nivel_ensino__pk__in=[NivelEnsino.GRADUACAO, NivelEnsino.POS_GRADUACAO])
                    if tipo_relatorio == PreencherRelatorioCensupForm.CAMPUS_ALUNO:
                        qs = qs.select_related('curso_campus', 'curso_campus__diretoria__setor').values_list('curso_campus__diretoria__setor__sigla', flat=True)
                    else:
                        qs = qs.select_related('curso_campus').values_list('curso_campus', flat=True)
            campus = format_(qs)
            if len(campus) < 10000:
                wsheet.write(row, coluna_salva, campus)
        except Exception as e:
            wsheet.write(row, coluna_salva, e)
    response = tempfile.NamedTemporaryFile(suffix='.xls', mode='w+b', delete=False)
    wworkbook.save(response)
    response.close()
    return task.finalize('Arquivo gerado com sucesso.', '..', file_path=response.name)


@task('Exportar Auditoria SUAP -> SISTEC para XLS')
def exportar_relatorio_alunos_nao_existentes_sistec_xls(planilha_path, campus_selecionado, anos_selecionados, convenios_selecionados, task=None):
    retry = 0
    while not os.path.exists(planilha_path) and retry < 60:
        sleep(2)
        retry += 1
    planilha = open(planilha_path, encoding="iso-8859-1")
    rows = list(csv.DictReader(planilha, delimiter=";"))
    wworkbook = xlwt.Workbook(encoding='utf-8')
    wsheet = wworkbook.add_sheet('Alunos')

    # Processando os alunos da planilha do SISTEC
    lista_alunos_sistec = []
    codigo_unidade = campus_selecionado.codigo_sistec

    for row in rows:
        try:
            codigo_curso = row['CO_CURSO']

            # Tratando o CPF - Se CPF vier mascarado retira a máscara e aplica novamente
            cpf_aluno = str(row['NU_CPF']).replace('.', '').replace('-', '')
            cpf_aluno = str(int(cpf_aluno))
            cpf_aluno = cpf_aluno.rjust(11, '0')
            cpf_aluno = mask_cpf(cpf_aluno)

            lista_alunos_sistec.append({'cpf': cpf_aluno, 'codigo_curso': codigo_curso, 'codigo_unidade': codigo_unidade})
        except Exception:
            pass

    # Criando a planilha que receberá os dados dos alunos que não constam na planilha do Sistec
    wsheet.write(0, 0, 'CPF')
    wsheet.write(0, 1, 'NOME')
    wsheet.write(0, 2, 'FORMA_INGRESSO')
    wsheet.write(0, 3, 'DIRETORIA')
    wsheet.write(0, 4, 'CURSO')
    wsheet.write(0, 5, 'CURSO_CODIGO_SISTEC')
    wsheet.write(0, 6, 'SITUACAO_MATRICULA')
    wsheet.write(0, 7, 'ANO_INGRESSO')
    wsheet.write(0, 8, 'PERIODO_INGRESSO')

    # Realizando o cruzamento dos alunos do SUAP com os da planilha do SISTEC
    qs_alunos = Aluno.objects.exclude(turmaminicurso__gerar_matricula=False).exclude(
        situacao__in=[
            SituacaoMatricula.CANCELADO,
            SituacaoMatricula.CANCELAMENTO_COMPULSORIO,
            SituacaoMatricula.CANCELAMENTO_POR_DUPLICIDADE,
            SituacaoMatricula.CANCELAMENTO_POR_DESLIGAMENTO,
            SituacaoMatricula.TRANSFERIDO_INTERNO,
            SituacaoMatricula.TRANSFERIDO_EXTERNO,
        ]
    )

    if convenios_selecionados:
        qs_alunos = qs_alunos.exclude(convenio__in=convenios_selecionados)

    qs_alunos = qs_alunos.filter(curso_campus__diretoria__setor__uo=campus_selecionado, ano_letivo__in=anos_selecionados)

    count = 1
    for aluno in task.iterate(qs_alunos):
        encontrado = False
        for codigo_sistec in aluno.curso_campus.codigo_sistec.split(';'):
            dict_aluno = {'cpf': aluno.pessoa_fisica.cpf, 'codigo_curso': codigo_sistec, 'codigo_unidade': aluno.curso_campus.diretoria.setor.uo.codigo_sistec}
            encontrado = encontrado or (dict_aluno in lista_alunos_sistec)
        if not encontrado:
            wsheet.write(count, 0, aluno.pessoa_fisica.cpf)
            wsheet.write(count, 1, aluno.pessoa_fisica.nome)
            wsheet.write(count, 2, str(aluno.forma_ingresso))
            wsheet.write(count, 3, str(aluno.curso_campus.diretoria))
            wsheet.write(count, 4, str(aluno.curso_campus))
            wsheet.write(count, 5, str(aluno.curso_campus.codigo_sistec))
            wsheet.write(count, 6, str(aluno.situacao))
            wsheet.write(count, 7, aluno.ano_letivo.ano)
            wsheet.write(count, 8, aluno.periodo_letivo)
            count += 1

    response = tempfile.NamedTemporaryFile(suffix='.xls', mode='w+b', delete=False)
    wworkbook.save(response)
    response.close()
    planilha.close()
    return task.finalize('Arquivo gerado com sucesso.', '..', file_path=response.name)


@task('Exportar Relatório de Idiomas sem Fronteira para XLS')
def exportar_relatorio_isf_xls(qs_aluno, task=None):
    rows = [['CODIGO_EMEC', 'CODIGO_CURSO', 'CURSO_NOME', 'CURSO_TIPO', 'CPF', 'CSF', 'INTEGRALIDADE', 'MEDIA', 'EMAIL', 'TURNO', 'BOLSISTAS JOVENS TALENTOS']]

    for aluno in task.iterate(qs_aluno):
        # Informar o código somente para os cursos de graduação.
        curso_codigo = 0
        if aluno.curso_campus.modalidade.nivel_ensino.id == NivelEnsino.GRADUACAO:
            curso_codigo = aluno.curso_campus.codigo

        # O texto deve conter até 100 caracteres.
        curso_nome = aluno.curso_campus.descricao_historico[:100]

        # Utilize o valor 1 quando for curso de graduação.
        # Utilize o valor 2 quando for programa de pós-graduação lato sensu.
        # Utilize o valor 3 quando for programa de pós-graduação stricto sensu mestrado.
        # Utilize o valor 4 quando for programa de pós-graduação stricto sensu doutorado.
        curso_tipo = 0
        modalidade = aluno.curso_campus.modalidade
        if modalidade.nivel_ensino.id == NivelEnsino.GRADUACAO:
            curso_tipo = 1
        elif modalidade.id == Modalidade.ESPECIALIZACAO:
            curso_tipo = 2
        elif modalidade.id == Modalidade.MESTRADO:
            curso_tipo = 3
        elif modalidade.id == Modalidade.DOUTORADO:
            curso_tipo = 4

        # Informar somente os números no campo cpf.
        try:
            cpf_limpo = re.sub(r'\D', '', aluno.pessoa_fisica.cpf)
        except Exception:
            cpf_limpo = ''

        # Utilize o valor 1 quando o aluno for da área prioritária do CsF.
        # Utilize o valor 0 quando o aluno NÃO for da área prioritária do CsF.
        csf = aluno.curso_campus.ciencia_sem_fronteira and 1 or 0

        # Informar a proporção cursada pelo aluno para conclusão do curso ou programa. O campo aceitará valores fracionários, com utilização de ponto (.) como separador e até duas casas decimais (Exemplo: 60.50).
        # Os cursos de graduação e os programas de pós-graduação que não tenham como identificar o valor, a posição deve ser preenchida com 0.00.
        # Os valores deverão ser maiores ou iguais a 0.00 e menores que 100.00, portanto até 99.99.
        integralidade = aluno.get_percentual_ch_componentes_cumpridos()
        if integralidade >= 100:
            integralidade = 99.99
        integralidade = format(integralidade, '.2f')

        # Informar a média do aluno no curso ou programa. O campo aceitará valores fracionários, com utilização de ponto (.) como separador e até duas casas decimais (Exemplo: 8.00).
        # Os cursos de graduação e os programas de pós-graduação que não tenham como identificar o valor, a posição deve ser preenchida com 0.00.
        # Os valores deverão ser maiores ou iguais a 0.00 e menores ou iguais a 100.00.
        media = aluno.get_ira()
        if media is None:
            media = 0
        media = format(media, '.2f')

        # Caso a instituição não tenha o e-mail de contato, o valor deve ser preenchido com email_nao_informado.
        # Deverá ser informado apenas um e-mail por aluno.
        email = aluno.pessoa_fisica.email or aluno.email_academico or 'email_nao_informado'

        # Utilize o valor 1 quando para o turno Matutino.
        # Utilize o valor 2 quando para o turno Vespertino.
        # Utilize o valor 3 quando para o turno Noturno.
        # Utilize o valor 4 quando para o turno Integral.
        turno = 0
        if aluno.turno:
            if aluno.turno.id == Turno.MATUTINO:
                turno = 1
            elif aluno.turno.id == Turno.VESPERTINO:
                turno = 2
            elif aluno.turno.id == Turno.NOTURNO:
                turno = 3
            elif aluno.turno.id == Turno.DIURNO:
                turno = 4

        row = [aluno.curso_campus.codigo_emec, curso_codigo, curso_nome, curso_tipo, cpf_limpo, csf, integralidade, media, email, turno, 0]
        rows.append(row)

    return XlsResponse(rows, processo=task)


@task('Exportar Dados para STTU')
def exportar_para_sttu(qs, task=None):
    from edu.sttu import Exportador
    Exportador(qs, task)


@task('Assinar Diplomas')
def assinar_diplomas_eletronicos(request, qs, task=None):
    for assinatura_eletronica in task.iterate(qs):
        assinatura_eletronica.assinar(request)
    return task.finalize('Assinatura realizada com sucesso.', '/admin/edu/assinaturaeletronica/?tab=tab_pendentes_usuario')


@task('Evadir Alunos em Lote')
def evadir_alunos_lote(alunos_selecionados, task=None):
    qtd_nao_evadidos = 0
    for aluno in task.iterate(alunos_selecionados):
        try:
            aluno.get_ultima_matricula_periodo().evadir('Evasão em Lote')
        except ValidationError:
            qtd_nao_evadidos += 1
    if qtd_nao_evadidos:
        mensagem = f'Não foi possível evadir {qtd_nao_evadidos} aluno(s). Verifique os períodos anteriores.'
    else:
        mensagem = 'Evasão em lote realizada com sucesso.'
    return task.finalize(mensagem, '/edu/evasao_em_lote/')
