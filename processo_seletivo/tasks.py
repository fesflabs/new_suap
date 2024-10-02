# -*- coding: utf-8 -*-
from datetime import datetime
from djtools.assincrono import task
from edu.models import Aluno, CursoCampus, SequencialMatricula, MatriculaPeriodo, SituacaoMatricula, SituacaoMatriculaPeriodo, Turno, LinhaPesquisa
from processo_seletivo.models import CandidatoVaga, Candidato, OfertaVaga, Lista, RotuloLista, OfertaVagaCurso
from comum.models import PessoaFisica
from xml.dom import minidom


@task('Importar Edital')
def importar_edital(xml, edital, task=None):
    doc = minidom.parseString(xml)
    task.count(doc.getElementsByTagName('lista'), doc.getElementsByTagName('vaga'), doc.getElementsByTagName('candidato'), doc.getElementsByTagName('candidato-vaga'))

    OfertaVaga.objects.filter(oferta_vaga_curso__edital=edital).update(qtd=0)

    for _lista in task.iterate(doc.getElementsByTagName('lista')):
        codigo = _lista.getElementsByTagName('codigo')[0].firstChild.nodeValue
        descricao = _lista.getElementsByTagName('descricao')[0].firstChild.nodeValue
        qs = Lista.objects.filter(codigo=codigo, edital=edital)
        if qs.exists():
            lista = qs[0]
        else:
            lista = Lista()
            lista.codigo = codigo
        lista.edital = edital
        lista.descricao = descricao
        lista.save()
        if not RotuloLista.objects.filter(nome=descricao).exists():
            RotuloLista.objects.create(nome=descricao)

    turnos = dict()
    for turno in Turno.objects.all():
        turnos[turno.descricao.upper()] = turno

    for _vaga in task.iterate(doc.getElementsByTagName('vaga')):
        codigo_curso = _vaga.getElementsByTagName('codigo-curso')[0].firstChild.nodeValue
        codigo_linha_pesquisa = _vaga.getElementsByTagName('linha-pesquisa')[0].firstChild and _vaga.getElementsByTagName('linha-pesquisa')[0].firstChild.nodeValue or 0
        linha_pesquisa = LinhaPesquisa.objects.filter(pk=codigo_linha_pesquisa).first()
        curso_campus = CursoCampus.objects.get(codigo=codigo_curso)
        codigo_lista = _vaga.getElementsByTagName('codigo-lista')[0].firstChild.nodeValue
        turno = turnos.get(_vaga.getElementsByTagName('turno')[0].firstChild and str(_vaga.getElementsByTagName('turno')[0].firstChild.nodeValue).upper() or '', None)
        qtd = int(_vaga.getElementsByTagName('quantidade')[0].firstChild.nodeValue)
        qtd_inscritos = int(_vaga.getElementsByTagName('numero-alunos')[0].firstChild and _vaga.getElementsByTagName('numero-alunos')[0].firstChild.nodeValue or 0)
        campus_polo = (
            _vaga.getElementsByTagName('campus-polo')
            and _vaga.getElementsByTagName('campus-polo')[0].firstChild
            and _vaga.getElementsByTagName('campus-polo')[0].firstChild.nodeValue
            or ''
        )
        qs_oferta_vaga_curso = OfertaVagaCurso.objects.filter(edital=edital, curso_campus__codigo=codigo_curso, turno=turno, campus_polo=campus_polo, linha_pesquisa=linha_pesquisa)

        if qs_oferta_vaga_curso.exists():
            oferta_vaga_curso = qs_oferta_vaga_curso[0]
        else:
            oferta_vaga_curso = OfertaVagaCurso()
            oferta_vaga_curso.edital = edital
            oferta_vaga_curso.curso_campus = curso_campus
            oferta_vaga_curso.turno = turno
            oferta_vaga_curso.campus_polo = campus_polo
        oferta_vaga_curso.linha_pesquisa = linha_pesquisa
        oferta_vaga_curso.qtd_inscritos += qtd_inscritos
        oferta_vaga_curso.save()
        qs = OfertaVaga.objects.filter(
            oferta_vaga_curso__edital=edital,
            oferta_vaga_curso__curso_campus__codigo=codigo_curso,
            lista__codigo=codigo_lista,
            oferta_vaga_curso__turno=turno,
            oferta_vaga_curso__campus_polo=campus_polo,
            oferta_vaga_curso__linha_pesquisa=linha_pesquisa,
        )

        if qs.exists():
            oferta_vaga = qs[0]
        else:
            oferta_vaga = OfertaVaga()
        oferta_vaga.oferta_vaga_curso = oferta_vaga_curso
        oferta_vaga.lista = Lista.objects.get(codigo=codigo_lista, edital=edital)
        oferta_vaga.qtd += qtd
        oferta_vaga.save()

    for _candidato in task.iterate(doc.getElementsByTagName('candidato')):
        inscricao = _candidato.getElementsByTagName('inscricao')[0].firstChild.nodeValue
        cpf = _candidato.getElementsByTagName('cpf')[0].firstChild.nodeValue
        nome = _candidato.getElementsByTagName('nome')[0].firstChild and _candidato.getElementsByTagName('nome')[0].firstChild.nodeValue or ''
        email = _candidato.getElementsByTagName('email')[0].firstChild and _candidato.getElementsByTagName('email')[0].firstChild.nodeValue or ''
        telefone = _candidato.getElementsByTagName('telefone')[0].firstChild and _candidato.getElementsByTagName('telefone')[0].firstChild.nodeValue or ''
        codigo_curso = _candidato.getElementsByTagName('codigo-curso')[0].firstChild and _candidato.getElementsByTagName('codigo-curso')[0].firstChild.nodeValue or ''
        turno = _candidato.getElementsByTagName('turno')[0].firstChild and str(_candidato.getElementsByTagName('turno')[0].firstChild.nodeValue).upper() or ''
        campus_polo = _candidato.getElementsByTagName('campus-polo')[0].firstChild and _candidato.getElementsByTagName('campus-polo')[0].firstChild.nodeValue or ''

        qs = Candidato.objects.filter(inscricao=inscricao, edital=edital)
        if qs.exists():
            candidato = qs[0]
        else:
            candidato = Candidato()
            candidato.inscricao = inscricao
            candidato.edital = edital
        candidato.email = email
        candidato.telefone = telefone
        candidato.cpf = cpf
        candidato.nome = nome
        candidato.curso_campus = CursoCampus.objects.get(codigo=codigo_curso)
        candidato.turno = turnos.get(turno, None)
        candidato.campus_polo = campus_polo
        candidato.save()

    for _candidato_vaga in task.iterate(doc.getElementsByTagName('candidato-vaga')):
        inscricao = _candidato_vaga.getElementsByTagName('inscricao')[0].firstChild.nodeValue
        codigo_curso = _candidato_vaga.getElementsByTagName('codigo-curso')[0].firstChild.nodeValue
        codigo_lista = _candidato_vaga.getElementsByTagName('codigo-lista')[0].firstChild.nodeValue
        codigo_linha_pesquisa = (
            _candidato_vaga.getElementsByTagName('linha-pesquisa')[0].firstChild and _candidato_vaga.getElementsByTagName('linha-pesquisa')[0].firstChild.nodeValue or 0
        )
        linha_pesquisa = LinhaPesquisa.objects.filter(pk=codigo_linha_pesquisa).first()
        candidato = Candidato.objects.get(inscricao=inscricao, edital=edital)
        classificacao = _candidato_vaga.getElementsByTagName('classificacao')[0].firstChild.nodeValue
        aprovado = _candidato_vaga.getElementsByTagName('aprovado')[0].firstChild.nodeValue == 'Sim'
        eliminado = _candidato_vaga.getElementsByTagName('eliminado')[0].firstChild.nodeValue == 'Sim'
        turno = _candidato_vaga.getElementsByTagName('turno')[0].firstChild and str(_candidato_vaga.getElementsByTagName('turno')[0].firstChild.nodeValue).upper() or ''

        qs_oferta_vaga = OfertaVaga.objects.filter(
            oferta_vaga_curso__edital=edital,
            oferta_vaga_curso__curso_campus__codigo=codigo_curso,
            lista__codigo=codigo_lista,
            oferta_vaga_curso__turno=turnos.get(turno),
            oferta_vaga_curso__linha_pesquisa=linha_pesquisa,
        )
        qs_oferta_vaga = qs_oferta_vaga.filter(oferta_vaga_curso__campus_polo=candidato.campus_polo)

        qs_candidato_vaga = CandidatoVaga.objects.filter(candidato=candidato, oferta_vaga=qs_oferta_vaga[0])
        if qs_candidato_vaga.exists():
            candidato_vaga = qs_candidato_vaga[0]
        else:
            candidato_vaga = CandidatoVaga()
            candidato_vaga.candidato = candidato
            candidato_vaga.oferta_vaga = qs_oferta_vaga[0]
        candidato_vaga.aprovado = aprovado
        candidato_vaga.eliminado = eliminado
        candidato_vaga.classificacao = classificacao
        candidato_vaga.save()

    for oferta_vaga_curso in edital.ofertavagacurso_set.all():
        oferta_vaga_curso.realizar_nova_chamada(True)

    task.finalize('Importação realizada com sucesso', '/processo_seletivo/edital/%s/' % edital.pk)


@task('Matricular Alunos PROITEC')
def matricular_alunos_proitec(edital, ano_letivo, periodo_letivo, matriz, task=None):
    candidatos_vaga = CandidatoVaga.objects.filter(oferta_vaga__oferta_vaga_curso__curso_campus__in=edital.get_ids_cursos_proitec(), oferta_vaga__oferta_vaga_curso__edital=edital)
    for candidato_vaga in task.iterate(candidatos_vaga):

        qs = Aluno.objects.filter(candidato_vaga=candidato_vaga)
        if qs.exists():
            aluno = qs[0]
            aluno.pessoa_fisica.cpf = candidato_vaga.candidato.cpf
            aluno.pessoa_fisica.nome = candidato_vaga.candidato.nome
            aluno.pessoa_fisica.save()

        else:
            pessoa_fisica = PessoaFisica()
            pessoa_fisica.cpf = candidato_vaga.candidato.cpf
            pessoa_fisica.nome = candidato_vaga.candidato.nome
            pessoa_fisica.save()

            aluno = Aluno()
            aluno.pessoa_fisica = pessoa_fisica

        aluno.ira = 0
        aluno.periodo_letivo = periodo_letivo
        aluno.ano_letivo = ano_letivo

        aluno.matriz = matriz
        aluno.curso_campus = candidato_vaga.oferta_vaga.oferta_vaga_curso.curso_campus

        if candidato_vaga.aprovado:
            aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.CONCLUIDO)
            if not aluno.dt_conclusao_curso:
                aluno.dt_conclusao_curso = datetime.today()
                aluno.ano_conclusao = aluno.ano_letivo.ano
        else:
            aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.NAO_CONCLUIDO)

        aluno.candidato_vaga = candidato_vaga
        if not aluno.matricula:
            prefixo = '%s%s%s' % (aluno.ano_letivo, aluno.periodo_letivo, aluno.curso_campus.codigo)
            aluno.matricula = SequencialMatricula.proximo_numero(prefixo)
        aluno.save()

        aluno.pessoa_fisica.username = aluno.matricula
        aluno.pessoa_fisica.save()

        qs_mp = aluno.matriculaperiodo_set.all()
        mp = qs_mp.exists() and qs_mp[0] or MatriculaPeriodo()
        mp.ano_letivo = aluno.ano_letivo
        mp.periodo_letivo = aluno.periodo_letivo
        if candidato_vaga.aprovado:
            mp.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.APROVADO)
        else:
            mp.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA)
        mp.periodo_matriz = 1
        mp.aluno = aluno
        mp.save()

    task.finalize('Matrículas realizadas com sucesso', '/processo_seletivo/edital/%s/' % edital.pk)
