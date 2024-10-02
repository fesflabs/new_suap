# -*- coding: utf-8 -*-

from django.conf import settings
from pedagogia.models import QuestionarioMatriz, ItemQuestionarioMatriz
from sys import stdout
from edu.models import CursoCampus


class DAO:
    @staticmethod
    def get_connection():
        """Conexão com SQL Server"""
        import pymssql

        return pymssql.connect(
            host=settings.ACADEMICO['DATABASE_HOST'],
            user=settings.ACADEMICO['DATABASE_USER'],
            password=settings.ACADEMICO['DATABASE_PASSWORD'],
            database=settings.ACADEMICO['DATABASE_NAME'],
            as_dict=True,
        )

    def importar_matrizes(self):
        sql = '''
        SELECT
                distinct(mc.COD_MATRIZ_CURRICULAR) as cod_matriz,
                dmc.N_PERIODO as periodo,
                d.DESC_HISTORICO as disciplina,
                st.DESCRICAO as nucleo,
                dmc.CREDITOS as aulas,
                d.SIGLA_DISCIPLINA as sigla,
                mc.COD_CURSO as codigo_curso
        FROM DISCIPLINAS_MATRIZES_CURRICULARES dmc
        JOIN SITUACOES_TABELAS st ON (st.NOME_TABELA = 'DISCIPLINAS_MATRIZES_CURRICULARES' and
                                     st.NOME_COLUNA = 'NUCLEO_DISCIPLINA' and
                                      st.VALOR = dmc.NUCLEO_DISCIPLINA)
        JOIN DISCIPLINAS d ON dmc.COD_DISCIPLINA = d.COD_DISCIPLINA
        JOIN MATRIZES_CURRICULARES mc ON dmc.COD_MATRIZ_CURRICULAR = mc.COD_MATRIZ_CURRICULAR
        JOIN MATRICULAS m ON mc.COD_MATRIZ_CURRICULAR = m.COD_MATRIZ_CURRICULAR
        WHERE dmc.OPTATIVA = 0 and m.SIT_MATRICULA in (0)
        ORDER BY mc.COD_MATRIZ_CURRICULAR, dmc.N_PERIODO, d.DESC_HISTORICO
        '''

        cur = DAO.get_connection().cursor()
        cur.execute(sql)
        row = cur.fetchone()
        # count = 0
        while row:
            # count+=1
            # if count > 10: break
            nucleo = ''
            nucleo_aux = len(row['sigla'].split('.')) > 1 and row['sigla'].split('.')[1] or ''
            disciplina_aux = row['disciplina'].split(' ')[0].lower()

            if nucleo_aux == 'ndp':
                nucleo = '2. Núcleo Didático Pedagógico'
            elif nucleo_aux == 'nep':
                nucleo = '3. Núcleo Epistemológico'
            elif nucleo_aux in ('nfd', 'fnd'):
                nucleo = '1. Núcleo Fundamental'
            elif disciplina_aux == 'seminário':
                nucleo = '5. Seminário Curriculares(Obrigatórias)'
            elif disciplina_aux == 'estágio':
                nucleo = '6. Prática Profissional'
            else:
                nucleo = '4. Núcleo Específico'

            curso_campus = CursoCampus.objects.get(codigo_academico=row['codigo_curso'])
            questionario_matriz, criado = QuestionarioMatriz.objects.get_or_create(academico_matriz=row['cod_matriz'], curso_campus=curso_campus)
            ItemQuestionarioMatriz.objects.get_or_create(
                questionario_matriz=questionario_matriz, disciplina=row['disciplina'], nucleo=nucleo, periodo=row['periodo'], aulas_por_semana=row['aulas'] or 0
            )

            row = cur.fetchone()
        cur.close()
        stdout.write("\rImportando matrizes : 100%\r\n")

    @staticmethod
    def get_matriz_aluno(matricula):
        sql = "SELECT cod_matriz_curricular as cod_matriz FROM matriculas m WHERE m.matricula = '%s'" % matricula
        cur = DAO.get_connection().cursor()
        cur.execute(sql)
        row = cur.fetchone()
        while row:
            return row['cod_matriz']
