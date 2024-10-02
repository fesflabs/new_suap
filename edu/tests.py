import datetime
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management import call_command
from comum.models import Ano, Predio, Sala, Configuracao, PrestadorServico, Municipio, Raca, Vinculo
from comum.models import User, UsuarioGrupo, UsuarioGrupoSetor
from comum.tests import SuapTestCase
from djtools.templatetags.filters import format_
from edu import q_academico
from edu.forms import AtividadeComplementarForm
from edu.models import (
    NivelEnsino,
    NaturezaParticipacao,
    Turno,
    FormaIngresso,
    Modalidade,
    Convenio,
    Nucleo,
    TipoProfessorDiario,
    SituacaoMatricula,
    SituacaoMatriculaPeriodo,
    HorarioCampus,
    Diretoria,
    CalendarioAcademico,
    EstruturaCurso,
    Componente,
    Matriz,
    CursoCampus,
    Turma,
    Diario,
    Professor,
    Aluno,
    MatriculaDiario,
    Estado,
    Cidade,
    Cartorio,
    AreaCurso,
    EixoTecnologico,
    SolicitacaoUsuario,
    SolicitacaoRelancamentoEtapa,
    TipoComponente,
    MaterialAula,
    MaterialDiario,
    ConfiguracaoLivro,
    RegistroEmissaoDiploma,
    MatrizCurso,
    ProfessorDiario,
    Aula,
    AbonoFaltas,
    EquivalenciaComponenteQAcademico,
    ProcedimentoMatricula,
    LinhaPesquisa,
    ProjetoFinal,
    ConfiguracaoAtividadeComplementar,
    TipoAtividadeComplementar,
    ItemConfiguracaoAtividadeComplementar,
    AtividadeComplementar,
    ComponenteCurricular,
    HistoricoRelatorio,
    Mensagem,
    ConfiguracaoPedidoMatricula,
    PedidoMatricula,
    HorarioAulaDiario,
    ConfiguracaoAvaliacao,
    ItemConfiguracaoAvaliacao,
    ConfiguracaoCertificadoENEM,
    SolicitacaoCertificadoENEM,
    RegistroEmissaoCertificadoENEM,
    Disciplina,
    NucleoCentralEstruturante,
    Polo,
    AtividadePolo,
    AreaCapes,
    ConvocacaoENADE,
    RegistroConvocacaoENADE,
    JustificativaDispensaENADE,
    MatriculaPeriodo,
)
from edu.models.cadastros_gerais import Pais
from processo_seletivo.models import CandidatoVaga, Edital, Lista, Candidato, WebService, OfertaVagaCurso
from protocolo.models import Processo
from rh.enums import Nacionalidade

q_academico.DAO = q_academico.MockDAO


class EduTestCase(SuapTestCase):
    SALVAR_NOVA_PLANILHA = True
    ANUAL = '1'
    SEMESTRAL = '2'
    LIVRE = '3'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        super().setUp()

        self.initial_data = dict()

        self.servidor_a.user.groups.add(Group.objects.get(name='Administrador Acadêmico'))
        self.servidor_a.user.save()

        self.servidor_c.user.groups.add(Group.objects.get(name='Diretor de Avaliação e Regulação do Ensino'))
        self.servidor_c.user.save()

        self.servidor_d.user.groups.add(Group.objects.get(name='Operador ENADE'))
        self.servidor_d.user.save()

        self.ano_2013 = Ano.objects.get_or_create(ano=2013)[0]
        self.ano_2014 = Ano.objects.get_or_create(ano=2014)[0]
        self.ano_atual = Ano.objects.get_or_create(ano=datetime.datetime.now().year)[0]

        Configuracao.objects.get_or_create(app='ldap_backend', chave='dominio_institucional', valor='ifrn.edu.br', descricao='...')
        Configuracao.objects.get_or_create(app='ldap_backend', chave='dominio_academico', valor='academico.ifrn.edu.br', descricao='...')
        Configuracao.objects.get_or_create(app='ldap_backend', chave='dominio_google_classroom', valor='escolar.ifrn.edu.br', descricao='...')

        Configuracao.objects.get_or_create(app='edu', chave='ano_letivo_atual', valor='2013')
        Configuracao.objects.get_or_create(app='edu', chave='periodo_letivo_atual', valor='2')

        # CADASTROS BÁSICOS
        pais = Pais.objects.get_or_create(nome='Brasil')[0]
        estado = Estado.objects.get_or_create(nome='Rio Grande do Norte', id=24)[0]
        cidade = Cidade.objects.get_or_create(nome='Natal', estado_id=estado.pk, cep_inicial='', cep_final='', codigo='2401403', pais_id=pais.pk)[0]
        Cartorio.objects.get_or_create(nome='Natal', cidade_id=cidade.pk, serventia='')
        predio = Predio.objects.get_or_create(nome='Prédio Padrão', uo=self.servidor_b.setor.uo, ativo=True)[0]
        Sala.objects.get_or_create(nome='Sala Padrão', ativa=True, predio=predio)

        self.raca = Raca.objects.get_or_create(descricao='Parda', codigo_censup='3', codigo_siape=4, inativo_siape=False)[0]

        self.carga_inicial()

    def tearDown(self):
        if SuapTestCase.allow_save_scenario():
            self.salvar_planilha(EduTestCase.SALVAR_NOVA_PLANILHA)
            if EduTestCase.SALVAR_NOVA_PLANILHA:
                EduTestCase.SALVAR_NOVA_PLANILHA = False

    def carga_inicial(self):
        """
        Cria os cadastros prévios necessários para a dinâmica da aplicação EDU, isto é, realiza os
        cadastros das macro atividades "Realizar Cadastros Gerais", "Vincular Usuários às Diretórias",
        "Configurar Horários dos Campi" e "Cadastrar Cursos".
        """

        # CADASTROS GERAIS
        self.acessar_como_administrador()
        area = self.cadastrar_area_curso('Educação')
        diretoria_academica = self.cadastrar_diretoria(self.servidor_b.setor.pk)
        eixo = self.cadastrar_eixo_tecnologico('Ambiente e Saúde')
        area_capes = self.cadastrar_area_capes('Ciências Exatas e da Terra')
        natureza_participacao = self.cadastrar_natureza_participacao('Presencial')
        nucleo = self.cadastrar_nucleo('Articulador')
        self.cadastrar_tipo_professor_diario('Principal')
        turno = self.cadastrar_turno('Matutino')
        self.cadastrar_disciplina_professor('Matemática')
        self.cadastrar_nucleo_central_estruturante('Biologia')

        # CADASTROS GERAIS FIC
        self.cadastrar_convenio('PRONATEC')
        self.cadastrar_forma_ingresso('Matrícula Direta')
        tipo_componente_fic = self.cadastrar_tipos_componente('FIC')

        # CADASTROS GERAIS PÓS
        self.cadastrar_tipo_atividade_complementar('Mesa Redonda')
        self.cadastrar_tipo_atividade_complementar('Palestra')

        # CADASTROS GERAIS PÓS - processo seletivo
        self.cadastrar_linha_pesquisa()
        self.cadastrar_forma_ingresso('Processo Seletivo')
        tipo_componente_pos = self.cadastrar_tipos_componente('POS')
        self.cadastrar_tipo_professor_diario('Principal')

        # CADASTROS GERAIS PÓS - integração Q-Acadêmico
        self.cadastrar_forma_ingresso('Integração Q-Acadêmico')

        # CADASTROS EAD
        self.cadastrar_polo()

        # VINCULAÇÃO DOS USUÁRIOS E CADASTRO DOS HORÁRIOS DAS AULAS
        self.vincular_usuario_a_diretoria('Secretário Acadêmico')
        self.configurar_horario_campus('Horário Padrão', turno, self.servidor_b.setor, ('07:00-08:00', '08:00-09:00', '10:00-11:00'))

        # CADASTRO DO CURSO FIC
        estrutura_fic = self.cadastrar_estrutura_curso(
            descricao='PRONATEC / FICs 75%', tipo_avaliacao=EstruturaCurso.TIPO_AVALIACAO_FIC, limite_reprovacao='0', qtd_minima_disciplinas='0'
        )
        componente_fic = self.cadastrar_componente_curricular(
            tipo_componente_fic,
            descricao='Administração da propriedade rural',
            descricao_historico='Administração da propriedade rural',
            tipo=tipo_componente_fic.pk,
            diretoria=diretoria_academica.pk,
            nivel_ensino=NivelEnsino.FUNDAMENTAL,
            ch_hora_relogio='10',
            ch_hora_aula='10',
            ch_qtd_creditos='10',
        )
        matriz_fic = self.cadastrar_matriz(
            descricao='FIC em Agricultor Familiar [PRONATEC]',
            ano_criacao=self.ano_2013.pk,
            nivel_ensino=NivelEnsino.FUNDAMENTAL,
            qtd_periodos_letivos='1',
            estrutura=estrutura_fic.pk,
            ch_componentes_obrigatorios='150',
            ch_componentes_tcc='0',
        )
        self.replicar_matriz()
        self.vincular_componente(matriz_fic, componente_fic, periodo_letivo='1', tipo='1', qtd_avaliacoes='1', nucleo=nucleo.pk, ch_presencial='10', ch_pratica='0')
        data = dict(
            descricao='FIC+ Agricultor Familiar [PRONATEC]',
            descricao_historico='Agricultor Familiar',
            ano_letivo=self.ano_2013.pk,
            periodo_letivo='1',
            data_inicio='17/06/2013',
            data_fim='',
            ativo='on',
            codigo='0981',
            natureza_participacao=natureza_participacao.pk,
            turno=turno.pk,
            modalidade=Modalidade.FIC,
            area=area.pk,
            eixo=eixo.pk,
            area_capes=area_capes.pk,
            estrutura=estrutura_fic.pk,
            periodicidade=CursoCampus.PERIODICIDADE_LIVRE,
            diretoria=diretoria_academica.pk,
            emite_diploma=True,
            titulo_certificado_masculino='Agricultor',
            titulo_certificado_feminino='Agricultora',
        )
        curso_fic = self.cadastrar_curso(data)
        self.replicar_curso()
        self.vincular_matriz_curso(matriz_fic, curso_fic)

        # CADASTRO DO CURSO PÓS
        estrutura_pos = self.cadastrar_estrutura_curso(
            descricao='PÓS-GRADUAÇAO (SERIADO)', tipo_avaliacao=EstruturaCurso.TIPO_AVALIACAO_SERIADO, limite_reprovacao='2', qtd_minima_disciplinas='3'
        )
        componente_pos_a = self.cadastrar_componente_curricular(
            tipo_componente_pos,
            descricao='Administração da propriedade rural',
            descricao_historico='Administração da propriedade rural',
            tipo=tipo_componente_pos.pk,
            diretoria=diretoria_academica.pk,
            nivel_ensino=NivelEnsino.POS_GRADUACAO,
            ch_hora_relogio='10',
            ch_hora_aula='10',
            ch_qtd_creditos='10',
        )
        componente_pos_b = self.cadastrar_componente_curricular(
            tipo_componente_pos,
            descricao='Ambulatório de dependência química',
            descricao_historico='Ambulatório de dependência química',
            tipo=tipo_componente_pos.pk,
            diretoria=diretoria_academica.pk,
            nivel_ensino=NivelEnsino.POS_GRADUACAO,
            ch_hora_relogio='10',
            ch_hora_aula='10',
            ch_qtd_creditos='10',
        )
        componente_pos_c = self.cadastrar_componente_curricular(
            tipo_componente_pos,
            descricao='Projeto Final',
            descricao_historico='projeto final',
            tipo=tipo_componente_pos.pk,
            diretoria=diretoria_academica.pk,
            nivel_ensino=NivelEnsino.POS_GRADUACAO,
            ch_hora_relogio='10',
            ch_hora_aula='10',
            ch_qtd_creditos='10',
        )

        matriz_pos = self.cadastrar_matriz(
            descricao='Mestrado em Agricultor Familiar',
            ano_criacao=self.ano_2013.pk,
            nivel_ensino=NivelEnsino.POS_GRADUACAO,
            qtd_periodos_letivos='3',
            estrutura=estrutura_pos.pk,
            ch_componentes_obrigatorios='20',
            ch_componentes_tcc='10',
        )
        self.vincular_componente(matriz_pos, componente_pos_a, periodo_letivo='1', tipo='1', qtd_avaliacoes='1', nucleo=nucleo.pk, ch_presencial='10', ch_pratica='0')
        self.vincular_componente(matriz_pos, componente_pos_b, periodo_letivo='2', tipo='1', qtd_avaliacoes='1', nucleo=nucleo.pk, ch_presencial='10', ch_pratica='0')
        self.vincular_componente(matriz_pos, componente_pos_c, periodo_letivo='3', tipo='4', qtd_avaliacoes='1', nucleo=nucleo.pk, ch_presencial='10', ch_pratica='0')
        data = dict(
            descricao='Mestrado em Agricultor Familiar',
            descricao_historico='Agricultor Familiar',
            ano_letivo=self.ano_2013.pk,
            periodo_letivo='1',
            data_inicio='17/06/2013',
            data_fim='',
            ativo='on',
            codigo='0989',
            natureza_participacao=natureza_participacao.pk,
            turno=turno.pk,
            modalidade=Modalidade.MESTRADO,
            area=area.pk,
            eixo=eixo.pk,
            area_capes=area_capes.pk,
            estrutura=estrutura_pos.pk,
            periodicidade=CursoCampus.PERIODICIDADE_SEMESTRAL,
            diretoria=diretoria_academica.pk,
            emite_diploma=True,
            titulo_certificado_masculino='Mestre',
            titulo_certificado_feminino='Mestra',
        )
        curso_pos = self.cadastrar_curso(data)
        self.vincular_matriz_curso(matriz_pos, curso_pos)

        # CADASTRO CURSOS PARA MATRÍCULA ONLINE
        estrutura_pos_seriado = self.cadastrar_estrutura_curso(
            descricao='PÓS-GRADUAÇAO SERIADO',
            ativo=True,
            tipo_avaliacao=EstruturaCurso.TIPO_AVALIACAO_SERIADO,
            limite_reprovacao='1',
            criterio_avaliacao=EstruturaCurso.CRITERIO_AVALIACAO_NOTA,
            media_aprovacao_sem_prova_final='70',
            media_evitar_reprovacao_direta='50',
            media_aprovacao_avaliacao_final='70',
            percentual_frequencia='75',
            ira=EstruturaCurso.IRA_ARITMETICA_NOTAS_FINAIS,
            qtd_periodos_conclusao=0,
            qtd_max_reprovacoes_periodo=0,
            qtd_max_reprovacoes_disciplina=0,
            percentual_max_aproveitamento=0,
            numero_max_certificacoes=0,
            media_certificacao_conhecimento=0,
        )

        estrutura_pos_credito = self.cadastrar_estrutura_curso(
            descricao='PÓS-GRADUAÇAO CRÉDITO',
            ativo=True,
            tipo_avaliacao=EstruturaCurso.TIPO_AVALIACAO_CREDITO,
            qtd_minima_disciplinas='1',
            numero_disciplinas_superior_periodo='1',
            qtd_max_periodos_subsequentes='1',
            numero_max_cancelamento_disciplina='1',
            criterio_avaliacao=EstruturaCurso.CRITERIO_AVALIACAO_NOTA,
            media_aprovacao_sem_prova_final='70',
            media_evitar_reprovacao_direta='50',
            media_aprovacao_avaliacao_final='70',
            percentual_frequencia='75',
            ira=EstruturaCurso.IRA_ARITMETICA_NOTAS_FINAIS,
            qtd_periodos_conclusao=0,
            qtd_max_reprovacoes_periodo=0,
            qtd_max_reprovacoes_disciplina=0,
            percentual_max_aproveitamento=0,
            numero_max_certificacoes=0,
            media_certificacao_conhecimento=0,
        )

        componente_pos_a1 = self.cadastrar_componente_curricular(
            tipo_componente_pos,
            descricao='A1',
            descricao_historico='A1',
            diretoria=diretoria_academica.pk,
            nivel_ensino=NivelEnsino.POS_GRADUACAO,
            ch_hora_relogio='10',
            ch_hora_aula='10',
            ch_qtd_creditos='4',
        )

        componente_pos_a2 = self.cadastrar_componente_curricular(
            tipo_componente_pos,
            descricao='A2',
            descricao_historico='A2',
            diretoria=diretoria_academica.pk,
            nivel_ensino=NivelEnsino.POS_GRADUACAO,
            ch_hora_relogio='10',
            ch_hora_aula='10',
            ch_qtd_creditos='4',
        )

        componente_pos_b1 = self.cadastrar_componente_curricular(
            tipo_componente_pos,
            descricao='B1',
            descricao_historico='B1',
            diretoria=diretoria_academica.pk,
            nivel_ensino=NivelEnsino.POS_GRADUACAO,
            ch_hora_relogio='10',
            ch_hora_aula='10',
            ch_qtd_creditos='4',
        )

        componente_pos_b2 = self.cadastrar_componente_curricular(
            tipo_componente_pos,
            descricao='B2',
            descricao_historico='B2',
            diretoria=diretoria_academica.pk,
            nivel_ensino=NivelEnsino.POS_GRADUACAO,
            ch_hora_relogio='10',
            ch_hora_aula='10',
            ch_qtd_creditos='4',
        )

        componente_pos_op1 = self.cadastrar_componente_curricular(
            tipo_componente_pos,
            descricao='OP1',
            descricao_historico='OP1',
            diretoria=diretoria_academica.pk,
            nivel_ensino=NivelEnsino.POS_GRADUACAO,
            ch_hora_relogio='10',
            ch_hora_aula='10',
            ch_qtd_creditos='4',
        )

        matriz_pos_optativa_credito = self.cadastrar_matriz(
            descricao='Mestrado',
            ano_criacao=self.ano_2013.pk,
            periodo_criacao='1',
            data_inicio='11/06/2013',
            data_fim='',
            ativo='on',
            nivel_ensino=NivelEnsino.POS_GRADUACAO,
            qtd_periodos_letivos='2',
            estrutura=estrutura_pos_credito.pk,
            ch_componentes_obrigatorios='40',
            ch_componentes_optativos='10',
            ch_componentes_eletivos='10',
            ch_seminarios='0',
            ch_componentes_tcc='10',
            ch_pratica_profissional='0',
            ch_atividades_complementares='0',
        )

        self.vincular_componente(
            matriz_pos_optativa_credito, componente_pos_a1, periodo_letivo='1', tipo='1', qtd_avaliacoes='1', nucleo=nucleo.pk, ch_presencial='10', ch_pratica='0'
        )
        self.vincular_componente(
            matriz_pos_optativa_credito, componente_pos_a2, periodo_letivo='1', tipo='1', qtd_avaliacoes='1', nucleo=nucleo.pk, ch_presencial='10', ch_pratica='0'
        )
        self.vincular_componente(
            matriz_pos_optativa_credito, componente_pos_b1, periodo_letivo='2', tipo='1', qtd_avaliacoes='1', nucleo=nucleo.pk, ch_presencial='10', ch_pratica='0'
        )
        self.vincular_componente(
            matriz_pos_optativa_credito, componente_pos_b2, periodo_letivo='2', tipo='1', qtd_avaliacoes='1', nucleo=nucleo.pk, ch_presencial='10', ch_pratica='0'
        )
        self.vincular_componente(matriz_pos_optativa_credito, componente_pos_op1, tipo='1', optativo=True, qtd_avaliacoes='1', nucleo=nucleo.pk, ch_presencial='10', ch_pratica='0')

        matriz_pos_optativa_seriado = self.cadastrar_matriz(
            descricao='Mestrado',
            ano_criacao=self.ano_2013.pk,
            periodo_criacao='1',
            data_inicio='11/06/2013',
            data_fim='',
            ativo='on',
            nivel_ensino=NivelEnsino.POS_GRADUACAO,
            qtd_periodos_letivos='2',
            estrutura=estrutura_pos_seriado.pk,
            ch_componentes_obrigatorios='40',
            ch_componentes_optativos='10',
            ch_componentes_eletivos='10',
            ch_seminarios='0',
            ch_componentes_tcc='10',
            ch_pratica_profissional='0',
            ch_atividades_complementares='0',
        )

        self.vincular_componente(
            matriz_pos_optativa_seriado, componente_pos_a1, periodo_letivo='1', tipo='1', qtd_avaliacoes='1', nucleo=nucleo.pk, ch_presencial='10', ch_pratica='0'
        )
        self.vincular_componente(
            matriz_pos_optativa_seriado, componente_pos_a2, periodo_letivo='1', tipo='1', qtd_avaliacoes='1', nucleo=nucleo.pk, ch_presencial='10', ch_pratica='0'
        )
        self.vincular_componente(
            matriz_pos_optativa_seriado, componente_pos_b1, periodo_letivo='2', tipo='1', qtd_avaliacoes='1', nucleo=nucleo.pk, ch_presencial='10', ch_pratica='0'
        )
        self.vincular_componente(
            matriz_pos_optativa_seriado, componente_pos_b2, periodo_letivo='2', tipo='1', qtd_avaliacoes='1', nucleo=nucleo.pk, ch_presencial='10', ch_pratica='0'
        )
        self.vincular_componente(matriz_pos_optativa_seriado, componente_pos_op1, tipo='1', optativo=True, qtd_avaliacoes='1', nucleo=nucleo.pk, ch_presencial='10', ch_pratica='0')

        data = dict(
            descricao='Mestrado Seriado',
            descricao_historico='Mestrado Seriado',
            ano_letivo=self.ano_2013.pk,
            periodo_letivo='1',
            data_inicio='17/06/2013',
            data_fim='',
            ativo='on',
            codigo='9999',
            natureza_participacao=natureza_participacao.pk,
            turno=turno.pk,
            modalidade=Modalidade.MESTRADO,
            area=area.pk,
            eixo=eixo.pk,
            area_capes=area_capes.pk,
            estrutura=estrutura_pos_seriado.pk,
            periodicidade=CursoCampus.PERIODICIDADE_SEMESTRAL,
            diretoria=diretoria_academica.pk,
            emite_diploma=True,
            titulo_certificado_masculino='Mestre',
            titulo_certificado_feminino='Mestra',
        )
        curso_pos_seriado = self.cadastrar_curso(data)
        self.vincular_matriz_curso(matriz_pos_optativa_seriado, curso_pos_seriado)

        data = dict(
            descricao='Mestrado Crédito',
            descricao_historico='Mestrado Crédito',
            ano_letivo=self.ano_2013.pk,
            periodo_letivo='1',
            data_inicio='17/06/2013',
            data_fim='',
            ativo='on',
            codigo='8888',
            natureza_participacao=natureza_participacao.pk,
            turno=turno.pk,
            modalidade=Modalidade.MESTRADO,
            area=area.pk,
            eixo=eixo.pk,
            area_capes=area_capes.pk,
            estrutura=estrutura_pos_credito.pk,
            periodicidade=CursoCampus.PERIODICIDADE_SEMESTRAL,
            diretoria=diretoria_academica.pk,
            emite_diploma=True,
            titulo_certificado_masculino='Mestre',
            titulo_certificado_feminino='Mestra',
        )
        curso_pos_credito = self.cadastrar_curso(data)
        self.vincular_matriz_curso(matriz_pos_optativa_credito, curso_pos_credito)

        # cadastrando professor servidor
        self.cadastrar_professor_servidor()
        self.acessar_como_professor()

    def recarregar(self, objeto):
        return objeto.__class__.objects.get(pk=objeto.pk)

    def retornar(self, cls, qtd=1, chaves={}):
        if self.initial_data.get(cls.__name__):
            return self.initial_data[cls.__name__]
        if chaves:
            return cls.objects.get(**chaves)
        if qtd == 1:
            return cls.objects.latest('id')
        else:
            return cls.objects.all().order_by('-id')[0:qtd]

    def salvar_planilha(self, novo=False):
        from django.apps import apps
        import xlwt
        import xlrd
        from os import path
        from xlutils.copy import copy

        FILE_PATH = '/tmp/planilha.xls'

        if path.exists(FILE_PATH) and not novo:
            book = copy(xlrd.open_workbook(FILE_PATH))
        else:
            book = xlwt.Workbook(encoding="utf-8")

        sheet = book.add_sheet(self.__class__.__name__)
        count = 0
        app = apps.get_app('edu')
        for model in apps.get_models(app):
            m2m = []
            fields = []
            for field in model._meta._many_to_many():
                m2m.append(field.name)
            for field in model._meta.fields:
                fields.append(field.name)
            rows = []
            columns = []
            for o in model.objects.all():
                row = []
                for field_name in fields:
                    if field_name not in m2m and not 'documento' in field_name:
                        v = hasattr(o, field_name) and getattr(o, field_name) or None
                        if not rows:
                            # verbose_name = model._meta.get_field(field_name).verbose_name
                            columns.append(field_name)
                        row.append(str(format_(v)))
                rows.append(row)

            if rows and not model.__name__.startswith('Log') and not model.__name__.startswith('Registro'):
                sheet.write(count, 0, model.__name__)
                count += 1
                for i, v in enumerate(columns):
                    sheet.write(count, i, v)
                count += 1
                for row in rows:
                    for i, v in enumerate(row):
                        sheet.write(count, i, v)
                    count += 1
                count += 2
        book.save(open(FILE_PATH, 'w+b'))

    def to_html(self, response):
        with open('/tmp/testcase.html', 'w') as f:
            f.write(response.content)

    def cadastrar(self, cls, data):
        qs = cls.objects.filter(descricao=data['descricao'])
        if qs:
            return qs[0]
        name = cls.__name__.lower()
        url = f'/admin/edu/{name}/'
        self.client.get(url)
        response = self.client.get(url)
        self.assertContains(response, cls._meta.verbose_name_plural, status_code=200)
        url = f'/admin/edu/{name}/add/'
        response = self.client.get(url)
        self.assertContains(response, f'Adicionar {cls._meta.verbose_name}', status_code=200)
        count = cls.objects.all().count()
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(cls.objects.all().count(), count + 1)
        return self.retornar(cls)

    def logout(self):
        self.client.get('/accounts/logout/')

    def acessar_como_administrador(self):
        self.logout()
        successful = self.client.login(username=self.servidor_a.user.username, password='123')
        self.assertEqual(successful, True)

    def acessar_como_secretario(self):
        self.logout()
        successful = self.client.login(username=self.servidor_b.user.username, password='123')
        self.assertEqual(successful, True)

    def acessar_como_regulador_avaliador(self):
        self.logout()
        successful = self.client.login(username=self.servidor_c.user.username, password='123')
        self.assertEqual(successful, True)

    def acessar_como_operador_enade(self):
        self.logout()
        successful = self.client.login(username=self.servidor_d.user.username, password='123')
        self.assertEqual(successful, True)

    def acessar_como_professor(self):
        self.logout()
        professor = self.retornar(Professor)
        self.client.login(username=professor.vinculo.user.username, password='123')

    def acessar_como_aluno(self):
        self.logout()
        aluno = self.retornar(Aluno)
        self.client.login(username=aluno.matricula, password='123')

    def cadastrar_area_curso(self, descricao):
        return self.cadastrar(AreaCurso, dict(descricao=descricao))

    def cadastrar_disciplina_professor(self, descricao):
        return self.cadastrar(Disciplina, dict(descricao=descricao))

    def cadastrar_nucleo_central_estruturante(self, descricao):
        return self.cadastrar(NucleoCentralEstruturante, dict(descricao=descricao))

    def atualizar_configuracao_avaliacao(self, configuracao_avaliacao, forma_calculo, itens, divisor=None):

        url = f'/admin/edu/configuracaoavaliacao/{configuracao_avaliacao.pk}/change/'
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Editar ')
        count = ConfiguracaoAvaliacao.objects.all().count()
        data = {
            'forma_calculo': forma_calculo,
            'itemconfiguracaoavaliacao_set-TOTAL_FORMS': len(itens),
            'itemconfiguracaoavaliacao_set-INITIAL_FORMS': configuracao_avaliacao.itemconfiguracaoavaliacao_set.count(),
            'itemconfiguracaoavaliacao_set-MAX_NUM_FORMS': '1000',
        }

        if divisor:
            data.update({'divisor': divisor})
        else:
            data.update({'divisor': ''})

        i = 0
        for item in itens:
            item_qs = configuracao_avaliacao.itemconfiguracaoavaliacao_set.all()
            item_avaliacao = item_qs.count() > i and item_qs[i] or None
            s = f'itemconfiguracaoavaliacao_set-{i:d}-id'
            data[s] = item_avaliacao and item_avaliacao.pk or ''
            s = f'itemconfiguracaoavaliacao_set-{i:d}-tipo'
            data[s] = item.get('tipo')
            s = f'itemconfiguracaoavaliacao_set-{i:d}-sigla'
            data[s] = item.get('sigla')
            s = f'itemconfiguracaoavaliacao_set-{i:d}-descricao'
            data[s] = item.get('sigla')
            s = f'itemconfiguracaoavaliacao_set-{i:d}-nota_maxima'
            data[s] = item.get('nota_maxima')
            if item.get('peso'):
                s = f'itemconfiguracaoavaliacao_set-{i}-peso'
                data[s] = item.get('peso')
            i += 1

        response = self.client.post(url, data, follow=True)
        self.assertEqual(ConfiguracaoAvaliacao.objects.all().count(), count)
        return self.retornar(ConfiguracaoAvaliacao)

    def cadastrar_diretoria(self, setor=None):
        if not setor:
            setor = self.servidor_b.setor.pk
        url = '/admin/edu/diretoria/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Diretoria Acadêmica', status_code=200)
        count = Diretoria.objects.all().count()
        data = dict(
            setor=setor,
            tipo=1,
            titulo_autoridade_maxima_masculino='Reitor',
            titulo_autoridade_maxima_feminino='Reitora',
            titulo_autoridade_uo_masculino='Diretor Geral',
            titulo_autoridade_uo_feminino='Diretora Geral',
            titulo_autoridade_diretoria_masculino='Diretor Acadêmico',
            titulo_autoridade_diretoria_feminino='Diretora Acadêmica',
        )
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(Diretoria.objects.all().count(), count + 1)
        return self.retornar(Diretoria)

    def cadastrar_eixo_tecnologico(self, descricao):
        return self.cadastrar(EixoTecnologico, dict(descricao=descricao))

    def cadastrar_area_capes(self, descricao):
        return self.cadastrar(AreaCapes, dict(descricao=descricao))

    def cadastrar_forma_ingresso(self, descricao):
        return self.cadastrar(FormaIngresso, dict(descricao=descricao, ativo=True))

    def cadastrar_convenio(self, descricao):
        return self.cadastrar(Convenio, dict(descricao=descricao))

    def cadastrar_natureza_participacao(self, descricao):
        return self.cadastrar(NaturezaParticipacao, dict(descricao=descricao))

    def cadastrar_nucleo(self, descricao):
        return self.cadastrar(Nucleo, dict(descricao=descricao))

    def cadastrar_linha_pesquisa(self):
        return self.cadastrar(LinhaPesquisa, dict(descricao="Educação"))

    def cadastrar_tipo_professor_diario(self, descricao):
        return self.cadastrar(TipoProfessorDiario, dict(descricao=descricao))

    def cadastrar_tipo_atividade_complementar(self, descricao):
        return self.cadastrar(TipoAtividadeComplementar, dict(descricao=descricao))

    def cadastrar_tipos_componente(self, descricao):
        url = '/admin/edu/tipocomponente/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Tipo de Componente', status_code=200)
        count = TipoComponente.objects.all().count()
        data = dict(descricao=descricao)
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(TipoComponente.objects.all().count(), count + 1)
        return self.retornar(TipoComponente)

    def cadastrar_turno(self, descricao):
        return self.cadastrar(Turno, dict(descricao=descricao))

    def vincular_usuario_a_diretoria(self, nome):
        usuario_grupo = UsuarioGrupo.objects.get_or_create(group=Group.objects.get(name=nome), user=self.servidor_b.user)[0]
        UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=self.servidor_b.setor)

    def configurar_horario_campus(self, descricao, turno, setor, lista_horarios):
        qs = HorarioCampus.locals.filter(descricao=descricao)
        if qs:
            return qs[0]
        url = '/admin/edu/horariocampus/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Horário do Campus', status_code=200)
        count = HorarioCampus.locals.all().count()
        data = {
            'descricao': descricao,
            'uo': setor.uo_id,
            'ativo': 'on',
            'horarioaula_set-TOTAL_FORMS': '3',
            'horarioaula_set-INITIAL_FORMS': '0',
            'horarioaula_set-MAX_NUM_FORMS': '1000',
        }

        i = 0
        for h in lista_horarios:
            s = f'horarioaula_set-{i:d}-id'
            data[s] = ''
            s = f'horarioaula_set-{i:d}-horario_campus'
            data[s] = ''
            s = f'horarioaula_set-{i:d}-numero'
            data[s] = i + 1
            s = f'horarioaula_set-{i:d}-turno'
            data[s] = turno.pk
            s = f'horarioaula_set-{i:d}-inicio'
            data[s] = h[0:5]
            s = f'horarioaula_set-{i:d}-termino'
            data[s] = h[6:11]
            i += 1

        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(HorarioCampus.locals.all().count(), count + 1)
        horario_campus = HorarioCampus.locals.all().order_by('-id')[0]
        self.assertEqual(horario_campus.horarioaula_set.count(), 3)

        url = f'/edu/horariocampus/{horario_campus.id}/'
        response = self.client.get(url)
        self.assertContains(response, horario_campus.descricao, status_code=200)

        return horario_campus

    def cadastrar_calendario_academico(self, ano=None, periodo=None, tipo=CalendarioAcademico.TIPO_TEMPORARIO, **params):
        if not ano:
            ano = self.ano_2013
        if not periodo:
            periodo = '1'

        url = '/admin/edu/calendarioacademico/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Calendário Acadêmico', status_code=200)
        count = CalendarioAcademico.locals.all().count()
        init = dict(
            descricao='Calendário 1',
            tipo=tipo,
            uo=self.servidor_b.setor.uo_id,
            ano_letivo=ano.pk,
            periodo_letivo=periodo,
            data_inicio=f'01/01/{ano.ano}',
            data_fim=f'31/07/{ano.ano}',
            data_fechamento_periodo=f'31/07/{ano.ano}',
            qtd_etapas='1',
            data_inicio_etapa_1=f'01/01/{ano.ano}',
            data_fim_etapa_1=f'31/07/{ano.ano}',
        )
        init.update(params)
        response = self.client.post(url, init)
        self.assert_no_validation_errors(response)
        self.assertEqual(CalendarioAcademico.locals.all().count(), count + 1)

        # acessando calendário academico
        calendario_academico = self.retornar(CalendarioAcademico)
        url = f'/edu/calendarioacademico/{calendario_academico.id}/'
        response = self.client.get(url)
        self.assertContains(response, calendario_academico.descricao, status_code=200)

        return self.retornar(CalendarioAcademico)

    def gerar_turmas_diarios(self, ano=None, periodo=None, periodo_matriz=None, optativas=False, qtd_turmas=1):
        if not ano:
            ano = self.ano_2013
        if not periodo:
            periodo = 1
        if not periodo_matriz:
            periodo_matriz = 1

        # acessando a página de geração de turmas
        url = '/edu/gerar_turmas/'
        response = self.client.get(url)
        self.assertContains(response, 'Gerar Turmas', status_code=200)
        numero_turmas_antes = Turma.objects.all().count()
        matriz_curso = self.retornar(MatrizCurso)
        turno = self.retornar(Turno)
        horario_campus = self.retornar(HorarioCampus)
        calendario_academico = self.retornar(CalendarioAcademico)

        # executando o primeiro passo do wizard
        data = dict(ano_letivo=ano.pk, periodo_letivo=periodo, matriz_curso=matriz_curso.pk, tipo_componente=optativas and '0' or '1')
        self.client.get(url, data)

        # executando o segundo passo do wizard
        data.update(
            dict(
                qtd_periodo_1=periodo_matriz == 1 and qtd_turmas or 0,
                turno_periodo_1=turno.pk,
                vagas_periodo_1='0',
                qtd_periodo_2=periodo_matriz == 2 and qtd_turmas or 0,
                turno_periodo_2=turno.pk,
                vagas_periodo_2='0',
                qtd_periodo_3=periodo_matriz == 3 and qtd_turmas or 0,
                turno_periodo_3=turno.pk,
                vagas_periodo_3='0',
            )
        )
        response = self.client.get(url, data)
        self.assert_no_validation_errors(response)

        # executando o terceiro passo do wizard
        qs_componentes = matriz_curso.matriz.componentecurricular_set.filter(optativo=optativas)
        if not optativas:
            qs_componentes = qs_componentes.filter(periodo_letivo=periodo_matriz)
        componentes = tuple(qs_componentes.values_list('id', flat=True))

        data.update(dict(horario_campus=horario_campus.pk, calendario_academico=calendario_academico.pk, componentes=componentes))
        response = self.client.get(url, data)
        self.assert_no_validation_errors(response)

        # executando o quarto e último passo do wizard
        data.update(dict(confirmacao='on'))
        response = self.client.get(url, data, follow=True)
        self.assert_no_validation_errors(response)

        if not optativas:
            numero_turmas_depois = Turma.objects.all().count()
            self.assertEqual(numero_turmas_depois, numero_turmas_antes + 1)

        # acessando o admin de turmas
        url = '/admin/edu/turma/'
        response = self.client.get(url)
        self.assertContains(response, matriz_curso.curso_campus.descricao_historico, status_code=200)

        return Turma.objects.all()

    def replicar_matriz(self):
        # replicando a matriz
        matriz = self.retornar(Matriz)
        url = f'/edu/replicar_matriz/{matriz.pk}/'
        self.client.get(url, follow=True)
        data = dict(descricao=f'{matriz.descricao} [REPLICADO]')
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, f'{matriz.descricao} [REPLICADO]', status_code=200)
        matriz_replicada = self.retornar(Matriz)
        self.assertEqual(matriz.componentecurricular_set.count(), matriz_replicada.componentecurricular_set.count())
        # deletando a matriz replicada
        matriz_replicada.delete()

    def replicar_curso(self):
        # replicando curso
        curso = self.retornar(CursoCampus)
        url = f'/edu/replicar_cursocampus/{curso.pk}/'
        self.client.get(url, follow=True)
        data = dict(diretoria=self.retornar(Diretoria).pk, codigo='01404')
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Curso replicado com sucesso.', status_code=200)
        curso_replicado = self.retornar(CursoCampus)
        self.assertEqual(curso.matrizcurso_set.count(), curso_replicado.matrizcurso_set.count())
        # deletando o curso replicado
        curso_replicado.delete()

    def vincular_matriz_curso(self, matriz=None, curso=None):
        # vinculando uma matriz ao curso
        if not matriz:
            matriz = self.retornar(Matriz)
        if not curso:
            curso = self.retornar(CursoCampus)
        url = f'/edu/cursocampus/{curso.pk}/'
        response = self.client.get(url)
        self.assertContains(response, curso.descricao, status_code=200)
        url = f'/edu/adicionar_matriz_curso/{curso.pk}/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Matriz', status_code=200)
        count = curso.matrizcurso_set.count()
        data = dict(curso_campus=curso.pk, matriz=matriz.pk)
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(curso.matrizcurso_set.count(), count + 1)
        matrizcurso = self.retornar(MatrizCurso)
        self.cadastrar_autorizacao_reconhecimento(matrizcurso)
        return matrizcurso

    def cadastrar_autorizacao_reconhecimento(self, matrizcurso):
        curso = matrizcurso.curso_campus
        matriz = matrizcurso.matriz
        url = f'/edu/cursocampus/{curso.pk}/?tab=matrizes'
        response = self.client.get(url)
        self.assertContains(response, matriz.descricao, status_code=200)

        url = f'/edu/autorizacao_matriz_curso/{matrizcurso.pk}/'
        response = self.client.get(url)
        data = dict(
            tipo='Lei Federal', data='10/10/2010', numero='123', numero_publicacao='123',
            data_publicacao='10/10/2010', veiculo_publicacao='DOU', secao_publicacao='1', pagina_publicacao='10'
        )
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)

        url = f'/edu/reconhecimento_matriz_curso/{matrizcurso.pk}/'
        response = self.client.get(url)
        data = dict(
            tipo='Lei Federal', data='10/10/2010', numero='123', validade='10/10/2100', numero_publicao='123',
            data_publicacao='10/10/2010', pagina_publicao='123', secao_publicao='1', veiculo_publicacao='DOU'
        )
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)

    def transferir_posse_etapa(self):
        self.transferir_posse_etapa_registro_escolar()
        self.transferir_posse_etapa_professor()

    def transferir_posse_etapa_registro_escolar(self):
        diario = self.retornar(Diario)
        # tranferindo a posse do diário do professor para o registro escolar
        url = f'/edu/transferir_posse_diario/{diario.pk}/{1}/{Diario.POSSE_REGISTRO_ESCOLAR}/'
        self.client.get(url)
        url = f'/edu/diario/{diario.pk}/?tab=notas_faltas'
        response = self.client.get(url)
        self.assertContains(response, 'Posse transferida com sucesso.')

    def transferir_posse_etapa_professor(self):
        diario = self.retornar(Diario)
        # tranferindo a posse do diário de volta para o professor
        url = f'/edu/transferir_posse_diario/{diario.pk}/{1}/{Diario.POSSE_PROFESSOR}/'
        self.client.get(url)
        url = f'/edu/diario/{diario.pk}/?tab=notas_faltas'
        response = self.client.get(url)
        self.assertContains(response, 'Posse transferida com sucesso.')

    def cadastrar_professor_servidor(self):
        professor = Professor.objects.get_or_create(vinculo=self.servidor_c.user.get_vinculo())[0]
        Group.objects.get(name='Professor').user_set.add(professor.vinculo.user)
        return professor

    def cadastrar_professor_nao_servidor(self):
        # acessando a página de listagem de professores e procurando o botão de cadastro
        url = '/admin/edu/professor/?tab=tab_nao_servidor'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Professor Prestador de Serviço')
        # acessando a página de cadastro de professor externo
        url = '/edu/cadastrar_professor_nao_servidor/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Professor Prestador de Serviço')
        # cadastrando um professor externo
        numero_pretadores_antes = PrestadorServico.objects.count()
        url = '/edu/cadastrar_professor_nao_servidor/'
        data = dict(nome='João Pereira da Silva', cpf='477.863.089-03', passaporte='', sexo='M', nacionalidade=Nacionalidade.BRASILEIRO_NATO, email='joao@silva.com.br', uo=self.servidor_b.setor.uo_id)
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        numero_pretadores_depois = PrestadorServico.objects.count()
        self.assertContains(response, 'Professor cadastrado com sucesso.')
        self.assertEqual(numero_pretadores_depois, numero_pretadores_antes + 1)

        # acessando o professor
        professor = self.retornar(Professor)
        url = f'/edu/professor/{professor.id}/'
        response = self.client.get(url)
        self.assertContains(response, professor.vinculo.pessoa.nome, status_code=200)

    def configurar_diario(self, diario=None):
        if not diario:
            diario = self.retornar(Diario)
        # acessando diarios
        url = '/admin/edu/diario/'
        response = self.client.get(url)
        self.assertContains(response, diario.componente_curricular, status_code=200)

        # acessando a página de visualização de diário na aba "Dados Gerais"
        url = f'/edu/diario/{diario.pk}/'
        response = self.client.get(url)
        self.assertContains(response, f'Diário ({diario.pk}) - {diario.componente_curricular.componente.sigla}', status_code=200)
        # localizando o link de acesso à página de definição de sala de aula
        url = f'/edu/definir_local_aula_diario/{diario.pk}/'
        self.assertContains(response, url)
        # acessando a página de definição de sala de aula
        response = self.client.get(url)
        self.assertContains(response, 'Definir Local de Aula', status_code=200)
        self.assertIsNone(diario.local_aula)
        data = dict(sala=self.retornar(Sala).pk)
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        diario = self.recarregar(diario)
        self.assertIsNotNone(diario.local_aula)
        # voltando para a página de detalhamento de diário na aba padrão
        url = f'/edu/diario/{diario.pk}/'
        response = self.client.get(url)
        # localizando o link de acesso à página de e definição de horário
        url = f'/edu/definir_horario_aula_diario/{diario.pk}/'
        self.assertContains(response, url)
        # acessando a página de definição de horário
        response = self.client.get(url)
        self.assertContains(response, 'Definir Horário de Aula', status_code=200)
        self.assertEqual(diario.horarioauladiario_set.count(), 0)
        horario_campus = diario.horario_campus
        horarios_aulas = horario_campus.horarioaula_set.all().order_by('-id')

        data = dict(horario=[f'{horarios_aulas[0].pk};{1}', f'{horarios_aulas[1].pk};{1}', f'{horarios_aulas[2].pk};{1}'])
        response = self.client.post(f'/edu/definir_horario_aula_diario/{diario.pk}/', data, follow=True)
        self.assertContains(response, 'Horário definido com sucesso', status_code=200)

        self.assertEqual(diario.get_horario_aulas(), '2M123')
        # voltando para a página de detalhamento de diário na aba padrão
        url = f'/edu/diario/{diario.pk}/'
        response = self.client.get(url)
        # localizando o link de acesso à página de definição de professor
        url = f'/edu/adicionar_professor_diario/{diario.pk}/'
        self.assertContains(response, url)
        # acessando a página de inclusão de professor
        tipo_professor_diario = self.retornar(TipoProfessorDiario)
        professor = self.retornar(Professor)
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Professor', status_code=200)
        self.assertEqual(diario.professordiario_set.count(), 0)
        # definindo professor no diário
        data = dict(
            diario=diario.pk,
            vinculo=professor.vinculo.pessoa.pk,
            tipo=tipo_professor_diario.pk,
            data_inicio_etapa_1=diario.calendario_academico.data_inicio_etapa_1.strftime("%d/%m/%Y"),
            data_fim_etapa_1=diario.calendario_academico.data_fim_etapa_1.strftime("%d/%m/%Y"),
            data_inicio_etapa_final=diario.calendario_academico.data_fim_etapa_1.strftime("%d/%m/%Y"),
            data_fim_etapa_final=diario.calendario_academico.data_fechamento_periodo.strftime("%d/%m/%Y"),
            percentual_ch=100,
            ativo=True,
        )
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(diario.professordiario_set.count(), 1)
        return diario

    def visualizar_locais_horario_aulas_professor(self):
        # acessando a pagina de locais e horários de aula
        url = '/edu/locais_aula_professor/'
        response = self.client.get(url)
        self.assertContains(response, 'Locais e Horários de Aula', status_code=200)

    def efetuar_matricula_institucional(
        self,
        cpf='047.704.024-14',
        nome='Carlos Breno Pereira Silva',
        data_nascimento='27/08/1984',
        responsavel='Maria Eliete da Silva Pereira',
        nome_mae='Maria Eliete da Silva Pereira',
        logradouro='Av. João XXIII',
        numero='708',
        bairro='Santos Reis',
        cep='59141-030',
    ):

        numero_alunos_antes = Aluno.objects.all().count()
        numero_vinculos_antes = Vinculo.objects.all().count()
        # acessando a página de realização de matrícula
        qs = CandidatoVaga.objects.all()
        if qs.exists():
            url = f'/edu/efetuar_matricula/{qs[0].pk}/'
            linha_pesquisa = self.retornar(LinhaPesquisa)
        else:
            url = '/edu/efetuar_matricula/'
            linha_pesquisa = None
        response = self.client.get(url)
        self.assertContains(response, 'Matrícula Institucional', status_code=200)
        cidade = Cidade.objects.get(codigo=2401403)
        cartorio = self.retornar(Cartorio)
        # executando o primeiro passo do wizard
        data = dict(nacionalidade=Aluno.TIPO_NACIONALIDADE_CHOICES[0][0], cpf=cpf)
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        # executando o segundo passo do wizard
        data.update(
            nome=nome,
            sexo='M',
            data_nascimento=data_nascimento,
            estado_civil=Aluno.ESTADO_CIVIL_CHOICES[0][0],
            responsavel=responsavel,
            nome_mae=nome_mae,
            parentesco_responsavel=Aluno.PARENTESCO_CHOICES[0][0],
            cpf_responsavel='263.458.470-97',
            logradouro=logradouro,
            numero=numero,
            bairro=bairro,
            cep=cep,
            cidade=cidade.pk,
            tipo_zona_residencial=Aluno.TIPO_ZONA_RESIDENCIAL_CHOICES[0][0],
        )
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        # executando o terceiro passo do wizard
        data.update(
            aluno_pne='Não',
            email_pessoal='carlos.silva@agmail.com',
            tipo_sanguineo=Aluno.TIPO_SANGUINEO_CHOICES[0][0],
            naturalidade=cidade.pk,
            raca=self.raca.pk,
            nivel_ensino_anterior=NivelEnsino.objects.get(pk=NivelEnsino.MEDIO).pk,
            ano_conclusao_estudo_anterior=self.ano_2013.pk,
            tipo_instituicao_origem=Aluno.TIPO_INSTITUICAO_ORIGEM_CHOICES[0][0],
        )
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        # executando o quarto passo do wizard
        data.update(tipo_certidao=Aluno.TIPO_CERTIDAO_CHOICES[0][0], cartorio=cartorio.pk)
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        # executando o quinto passo do wizard
        turno = self.retornar(Turno)
        forma_ingresso = self.retornar(FormaIngresso)
        matriz_curso = self.retornar(MatrizCurso)
        convenio = self.retornar(Convenio)

        data.update(
            foto='',
            ano_letivo=self.ano_2013.pk,
            periodo_letivo=Aluno.PERIODO_LETIVO_CHOICES[0][0],
            turno=turno.pk,
            forma_ingresso=forma_ingresso.pk,
            cota_sistec=Aluno.COTA_SISTEC_CHOICES[0][0],
            cota_mec=Aluno.COTA_MEC_CHOICES[0][0],
            data_conclusao_intercambio='',
            matriz_curso=matriz_curso.pk,
            linha_pesquisa=linha_pesquisa and linha_pesquisa.pk or '',
            numero_pasta=3880,
            polo='',
            possui_convenio=True,
            convenio=convenio.pk,
        )
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)

        numero_alunos_depois = Aluno.objects.all().count()
        numero_vinculos_depois = Vinculo.objects.all().count()
        self.assertEqual(numero_alunos_depois, numero_alunos_antes + 1)
        self.assertEqual(numero_vinculos_depois, numero_vinculos_antes + 1)
        aluno = self.retornar(Aluno)

        # acessando o admin de alunos
        url = '/admin/edu/aluno/'
        response = self.client.get(url)
        self.assertContains(response, aluno.pessoa_fisica.nome, status_code=200)

        # alterando a senha do usuário do aluno para que ele possa acessar o suap
        user = User.objects.get(username=aluno.matricula)
        user.set_password('123')
        user.save()
        return aluno

    def cancelar_matricula(self):
        aluno = self.retornar(Aluno)
        numero_aluno_antes = Aluno.objects.count()
        url = f'/comum/excluir/edu/aluno/{aluno.pk}/'
        self.client.get(url, follow=True)
        data = dict(senha='123')
        response = self.client.post(url, data, follow=True)
        numero_aluno_depois = Aluno.objects.count()
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Registro(s) excluído(s) com sucesso.')
        self.assertEqual(numero_aluno_depois, numero_aluno_antes - 1)

    def emitir_relatorio_alunos(self):
        aluno = self.retornar(Aluno)
        # selecionando um aluno do formulário de listagem de alunos
        parameters = 'aluno={}&periodo_letivo=0&situacao_diario=0&periodo_ingresso=0&forma_ingresso=&formatacao=simples&quantidade_itens=25&ordenacao=Nome&agrupamento=Campus'.format(
            aluno.pk
        )
        url = '/edu/relatorio/?' + parameters
        response = self.client.get(url, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Carlos Breno Pereira Silva')
        # imprimindo os alunos selecionados
        response = self.client.get(url + "&imprimir=1&html=1", follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Carlos Breno Pereira Silva')
        # gerando o xls dos alunos selecionados
        response = self.client.get(url + "&xls=1", follow=True)
        self.assert_no_validation_errors(response)
        # salvando o relatorio
        before = HistoricoRelatorio.objects.count()
        data = dict(descricao='Relatório #1')
        response = self.client.post('/edu/salvar_relatorio/1/{}/'.format(parameters.encode("utf-8").hex()), data, follow=True)
        self.assert_no_validation_errors(response)
        after = HistoricoRelatorio.objects.count()
        self.assertEqual(before + 1, after)
        self.assertContains(response, 'Consulta salva com sucesso.')
        historico_relatorio = self.retornar(HistoricoRelatorio)
        # visualizando relatorio salvo
        response = self.client.get(historico_relatorio.get_url())
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Carlos Breno Pereira Silva')
        # apagando o relatorio salvo
        before = HistoricoRelatorio.objects.count()
        url = f'/comum/excluir/edu/historicorelatorio/{historico_relatorio.pk}/'
        response = self.client.get(url)
        data = dict(senha='123')
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Registro(s) excluído(s) com sucesso.', status_code=200)
        after = HistoricoRelatorio.objects.count()
        self.assertEqual(before, after + 1)

    def emitir_relatorio_diarios(self):
        ano_letivo = self.ano_2013
        # selecionando um ano ao formulário de listagem de diário
        parameters = f'ano_letivo={ano_letivo.pk}&periodo_letivo=&etapa=1&ordenacao=Nome&agrupamento=Campus'
        url = '/edu/relatorio_diario/?' + parameters
        response = self.client.get(url, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Ano Letivo')
        # imprimindo os diários selecionados
        response = self.client.get(url + "&imprimir=1&html=1", follow=True)
        self.assert_no_validation_errors(response)
        # gerando o xls dos diários selecionados
        response = self.client.get(url + "&xls=1", follow=True)
        self.assert_no_validation_errors(response)
        # salvando o relatorio
        before = HistoricoRelatorio.objects.count()
        data = dict(descricao='Relatório #1')
        response = self.client.post('/edu/salvar_relatorio/2/{}/'.format(parameters.encode("utf-8").hex()), data, follow=True)
        self.assert_no_validation_errors(response)
        after = HistoricoRelatorio.objects.count()
        self.assertEqual(before + 1, after)
        self.assertContains(response, 'Consulta salva com sucesso.')
        historico_relatorio = self.retornar(HistoricoRelatorio)
        # visualizando relatorio salvo
        response = self.client.get(historico_relatorio.get_url())
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'FIC.0001 - Administração da propriedade rural')
        # apagando o relatorio salvo
        before = HistoricoRelatorio.objects.count()
        url = f'/comum/excluir/edu/historicorelatorio/{historico_relatorio.pk}/'
        data = dict(senha='123')
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Registro(s) excluído(s) com sucesso.', status_code=200)
        after = HistoricoRelatorio.objects.count()
        self.assertEqual(before, after + 1)

    def emitir_relatorio_professores(self):
        # selecionando um professor do formulário de listagem de professores
        parameters = 'categoria=Todos&ano_letivo=&periodo_letivo=&tipo_professor=&uo=&setor_lotacao=&setor_suap=&disciplina_ingresso=&jornada_trabalho=&regime=Todos&nce=&ordenacao=Nome&exibicao=vinculo.setor.uo&exibicao=disciplina'
        url = '/edu/relatorio_professor/?' + parameters
        response = self.client.get(url, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Servidor 3')
        # imprimindo os professores selecionados
        response = self.client.get(url + "&imprimir=1&html=1", follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Servidor 3')
        # gerando o xls dos professores selecionados
        response = self.client.get(url + "&xls=1", follow=True)
        self.assert_no_validation_errors(response)
        # salvando o relatorio
        before = HistoricoRelatorio.objects.count()
        data = dict(descricao='Relatório #1')
        response = self.client.post('/edu/salvar_relatorio/3/{}/'.format(parameters.encode("utf-8").hex()), data, follow=True)
        self.assert_no_validation_errors(response)
        after = HistoricoRelatorio.objects.count()
        self.assertEqual(before + 1, after)
        self.assertContains(response, 'Consulta salva com sucesso.')
        historico_relatorio = self.retornar(HistoricoRelatorio)
        # visualizando relatorio salvo
        response = self.client.get(historico_relatorio.get_url())
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Servidor 3')
        # apagando o relatorio salvo
        before = HistoricoRelatorio.objects.count()
        url = f'/comum/excluir/edu/historicorelatorio/{historico_relatorio.pk}/'
        data = dict(senha='123')
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Registro(s) excluído(s) com sucesso.', status_code=200)
        after = HistoricoRelatorio.objects.count()
        self.assertEqual(before, after + 1)

    def emitir_relatorio_faltas(self, codigo_turma, contendo=None):
        # selecionando uma turma
        turma = Turma.objects.get(codigo=codigo_turma)
        parameters = f'turma={codigo_turma}&turma={turma.pk}&diario=&diario=&aluno=&aluno=&situacao_periodo=&intervalo_inicio=&intervalo_fim='
        url = '/edu/relatorio_faltas/?' + parameters
        response = self.client.get(url)
        self.assert_no_validation_errors(response)

        if contendo:
            self.assertContains(response, contendo)

    def relatorio_periodos_abertos(self, ano, contem, contendo):
        url = f'/edu/relatorio_periodos_abertos/?ano_selecionado={ano}'
        response = self.client.get(url)
        self.assertContains(response, 'Relatório de Alunos com Períodos Não-Fechados')

        if contem:
            self.assertContains(response, contendo)
        else:
            self.assertNotContains(response, contendo)

    def emitir_relatorio_ead(self):
        url = '/edu/relatorio_ead/'
        response = self.client.get(url)
        self.assertContains(response, 'Total de Alunos por Polo e Nível de Ensino')

    def relatorio_estatisticas(self):
        # acessando estatísticas
        url = '/edu/estatistica/'
        response = self.client.get(url)
        self.assertContains(response, 'Estatísticas')

        # acessando as estatísticas dos alunos matriculados a partir do ano de 2013
        url = f'/edu/estatistica/?tab=listagem&situacao_matricula_periodo=SITUACAO_MATRICULADO&periodicidade=por_ano_letivo&apartir_do_ano={self.ano_2013.pk}'
        response = self.client.get(url)
        self.assertContains(response, self.retornar(Aluno).pessoa_fisica.nome)

    def imprimir_comprovante_matricula(self):
        aluno = self.retornar(Aluno)
        # acessando o comprovante de matricula
        url = f'/edu/comprovante_matricula_pdf/{aluno.id}/?html=1'
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'COMPROVANTE DE MATRÍCULA')

    def visualizar_dados_pessoais_e_academicos(
        self, ja_selecionou_email=False, com_boletim=True, com_historico=True, com_atividades_complementares=False, com_procedimento_academico=False
    ):
        aluno = self.retornar(Aluno)
        response = self.client.get('/')
        self.assertContains(response, 'Responda ao questionário de Caracterização Socioeconômica')
        # self.assertContains(response, 'Calendário Acadêmico')
        if not ja_selecionou_email and 'ldap_backend' in settings.INSTALLED_APPS:
            self.assertContains(response, 'Escolha seu email Acadêmico')
        # acessando os dados pessoais do aluno
        url = aluno.get_absolute_url()
        response = self.client.get(url)
        self.assertContains(response, 'Dados Gerais')
        # acessando os dados acadêmicos do aluno
        response = self.client.get('{}{}'.format(url, '?tab=dados_pessoais'))
        self.assertContains(response, 'Dados Gerais')
        # acessando o boletim
        if com_boletim:
            response = self.client.get('{}{}'.format(url, '?tab=boletim'))
            self.assertContains(response, 'Gráfico de Desempenho por Etapa')
        # acessando o histórico
        if com_historico:
            response = self.client.get('{}{}'.format(url, '?tab=historico'))
            self.assertContains(response, 'Componentes Curriculares')
        # acessando os projetos finais
        response = self.client.get('{}{}'.format(url, '?tab=projeto'))
        if aluno.matriz:
            if aluno.matriz.exige_tcc:
                if not aluno.get_projetos_finais().exists():
                    self.assertContains(response, 'Não há trabalho de conclusão de curso para esse aluno')
                else:
                    projeto_final = self.retornar(ProjetoFinal)
                    self.assertContains(response, projeto_final.titulo)
            # acessando os requisitos de conclusão
            response = self.client.get('{}{}'.format(url, '?tab=requisitos'))
            self.assertContains(response, 'Disciplinas Obrigatórias')
        if not com_atividades_complementares:
            # acessando as atividades complementares
            response = self.client.get('{}{}'.format(url, '?tab=acc'))
            self.assertContains(response, 'Nenhuma atividade complementar cadastrada até o momento')

    def atualizar_endereco(self):
        aluno = self.retornar(Aluno)
        # atualizando endereço do aluno
        url = f'/edu/atualizar_meus_dados_pessoais/{aluno.matricula}/'
        response = self.client.get(url)
        cidade = Cidade.objects.get(codigo=2401403)
        self.assertContains(response, 'Atualização de Dados Pessoais')

        data = dict(
            email_secundario='a@a.com',
            logradouro='RUA LAGOA DOS PATOS',
            numero='100',
            complemento='APTO 101',
            bairro='LAGOA NOVA',
            cep='59300-000',
            cidade=cidade.pk,
            utiliza_transporte_escolar_publico='Não',
        )
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        aluno = self.recarregar(aluno)
        self.assertEqual(aluno.logradouro, 'RUA LAGOA DOS PATOS')

    def definir_email_institucional(self):
        if 'ldap_backend' not in settings.INSTALLED_APPS:
            return
        self.retornar(Aluno)
        response = self.client.get('/')
        # escolhendo o email institucional
        self.assertContains(response, 'Escolha seu email Acadêmico')
        url = '/ldap_backend/escolher_email/academico/'
        response = self.client.get('/ldap_backend/escolher_email/academico/')
        self.assertContains(response, 'Escolha seu E-mail Acadêmico', status_code=200)
        data = dict(email='carlos.silva@academico.ifrn.edu.br')
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'O email &quot;{}&quot; foi definido com sucesso e estará disponível para uso em 2 horas.'.format(data['email']), status_code=200)

    def visualizar_locais_horario_aulas_aluno(self):
        # acessando a pagina de locais e horários de aula
        aluno = self.retornar(Aluno)
        url = f'{aluno.get_absolute_url()}?tab=locais_aula_aluno'
        response = self.client.get(url)
        self.assertContains(response, 'Locais e Horários de Aula / Atividade', status_code=200)

    def lancar_aulas_faltas_professor(self, ano=None):
        if not ano:
            ano = self.ano_2013

        matricula_diario = self.retornar(MatriculaDiario)
        professor_diario = self.retornar(ProfessorDiario)
        # verificando a existência do link de acesso à página de visualização de etapa
        url = f'/edu/meu_diario/{matricula_diario.diario.pk}/1/'
        response = self.client.get(url)
        self.assertContains(response, url, status_code=200)
        # acessando a página de visualização da etapa 1, na aba "Aulas e Conteúdo"
        self.client.get(url)
        # verificando a existência do link de acesso à página de cadastro de aula
        url = f'/edu/adicionar_aula_diario/{matricula_diario.diario.pk}/1/'
        # self.assertContains(response, url)
        # acessando a página de cadastro de aula
        self.client.get(url)
        # registrando uma aula para atingir 80% da carga horária necessária (8 de 10)

        self.assertEqual(matricula_diario.diario.get_horas_aulas_etapa_1(), 0)
        data = dict(professor_diario=professor_diario.pk, etapa='1', quantidade='8', tipo=1, data=f'01/01/{ano.ano}', conteudo='Aula 01.')
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        matricula_diario = self.retornar(MatriculaDiario)
        self.assertFalse(matricula_diario.is_carga_horaria_diario_fechada())
        self.assertEqual(matricula_diario.get_situacao_frequencia()['rotulo'], 'Cursando')
        self.assertEqual(matricula_diario.get_situacao_nota()['rotulo'], 'Cursando')
        if matricula_diario.diario.pode_ser_entregue_sem_nota():
            self.assertEqual(matricula_diario.get_situacao_diario()['rotulo'], 'Pendente')
            self.assertTrue(matricula_diario.pode_fechar_periodo_letivo())
        else:
            self.assertEqual(matricula_diario.get_situacao_diario()['rotulo'], 'Cursando')
            self.assertFalse(matricula_diario.pode_fechar_periodo_letivo())
        self.assertEqual(matricula_diario.get_situacao_registrada_diario()['rotulo'], 'Cursando')
        self.assertTrue(matricula_diario.is_cursando())
        self.assertFalse(matricula_diario.realizou_todas_avaliacoes_regulares())
        self.assertFalse(matricula_diario.realizou_todas_avaliacoes())
        self.assertFalse(matricula_diario.is_aprovado_sem_prova_final())
        self.assertFalse(matricula_diario.realizou_avaliacao_final())
        self.assertFalse(matricula_diario.is_em_prova_final())
        self.assertFalse(matricula_diario.is_aprovado_em_prova_final())
        self.assertFalse(matricula_diario.is_aprovado_por_nota())
        self.assertTrue(matricula_diario.is_aprovado_por_frequencia())
        self.assertFalse(matricula_diario.is_aprovado())
        self.assertEqual(matricula_diario.get_media_disciplina(), None)
        self.assertEqual(matricula_diario.get_media_final_disciplina(), None)
        self.assertEqual(matricula_diario.get_numero_faltas_primeira_etapa(), 0)
        self.assertEqual(matricula_diario.get_percentual_carga_horaria_frequentada(), 100)
        # lançando mais uma aula para atingir de 100% necessário para fechar o diário
        data = dict(professor_diario=professor_diario.pk, etapa='1', quantidade='2', tipo=1, data=f'02/01/{ano.ano}', conteudo='Aula 02.')
        self.client.post(url, data)
        # verificando algumas condições acerca da carga horária
        temp = Diario.locals.get(pk=matricula_diario.diario.pk)
        self.assertEqual(temp.get_horas_aulas_etapa_1(), 10)
        self.assertEqual(temp.get_percentual_carga_horaria_cumprida(), 100)
        matricula_diario = MatriculaDiario.objects.get(pk=matricula_diario.pk)
        self.assertTrue(matricula_diario.is_carga_horaria_diario_fechada())
        self.assertEqual(matricula_diario.get_situacao_frequencia()['rotulo'], 'Aprovado')
        # voltando para a página de listagem de diários
        url = '/edu/meus_diarios/'
        self.client.get(url)
        # acessando a página de visualização de diário na aba "Chamada"
        url = f'/edu/meu_diario/{matricula_diario.diario.pk}/1/?tab=notas_faltas'
        response = self.client.get(url)
        # lançando uma falta
        aula_ = matricula_diario.diario.professordiario_set.all()[0].aula_set.all()[0]
        url_ = f'/edu/registrar_chamada_ajax/{matricula_diario.pk}/{aula_.pk}/1/'
        self.assertContains(response, url, status_code=200)
        response_ = self.client.get(url_)
        self.assertContains(response_, 'OK', status_code=200)

    def abonar_falta(self):
        matricula_diario = self.retornar(MatriculaDiario)
        aluno = matricula_diario.matricula_periodo.aluno

        # acessando a página para cadastrar abono de faltas
        url = '/admin/edu/abonofaltas/add/'
        response = self.client.get(url)
        # verificando se estou na página de cadastro de abono de faltas
        self.assertContains(response, 'Adicionar Justificativa de Falta', status_code=200)

        # guardando quantidade de faltas e abonos ANTES do cadastro de um abono
        qtd_faltas_diario_antes = matricula_diario.falta_set.all().count()
        qtd_faltas_periodo_antes = matricula_diario.matricula_periodo.get_total_faltas()
        qtd_faltas_abonadas_antes = matricula_diario.falta_set.filter(abono_faltas__isnull=False).all().count()

        data = dict(
            aluno=aluno.pk,
            responsavel_abono=self.servidor_a.user.pk,
            data_inicio='01/01/2013',
            data_fim='01/01/2013',
            justificativa='.',
            anexo='',
            diario=matricula_diario.diario.pk,
        )
        self.client.post(url, data)

        # guardando quantidade de faltas e abonos DEPOIS do cadastro de um abono
        qtd_faltas_diario_depois = matricula_diario.falta_set.all().count()
        qtd_faltas_abonadas_depois = matricula_diario.falta_set.filter(abono_faltas__isnull=False).all().count()
        qtd_faltas_periodo_depois = matricula_diario.matricula_periodo.get_total_faltas()

        # regras para verificar situação das faltas e abonos depois de um cadastro de abono
        self.assertEqual(qtd_faltas_diario_antes, qtd_faltas_diario_depois)
        self.assertEqual(qtd_faltas_periodo_depois, qtd_faltas_periodo_antes - 1)
        self.assertEqual(qtd_faltas_abonadas_depois, qtd_faltas_abonadas_antes + 1)

        # acessando a tela de visualização do abono de faltas
        ultimo_abono_faltas_cadastrado = self.retornar(AbonoFaltas)
        url = f'/edu/abonofaltas/{ultimo_abono_faltas_cadastrado.pk}/'
        response = self.client.get(url)
        # verificando se estou na página de visualização de abono de faltas
        self.assertContains(response, f'Justificativa de Falta - {ultimo_abono_faltas_cadastrado.aluno}', status_code=200)

        # guardando quantidade de faltas e abonos ANTES da exclusão de um abono
        qtd_faltas_diario_antes_exclusao = qtd_faltas_diario_depois
        qtd_faltas_abonadas_antes_exclusao = qtd_faltas_abonadas_depois
        qtd_faltas_periodo_antes_exclusao = qtd_faltas_periodo_depois

        # excluindo um abono faltas
        url = f'/comum/excluir/edu/abonofaltas/{ultimo_abono_faltas_cadastrado.pk}/'
        data = dict(senha='123')
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Registro(s) excluído(s) com sucesso.', status_code=200)

        # guardando quantidade de faltas e abonos DEPOIS DA EXCLUSÃO de um abono
        qtd_faltas_diario_depois_exclusao = matricula_diario.falta_set.all().count()
        qtd_faltas_abonadas_depois_exclusao = matricula_diario.falta_set.filter(abono_faltas__isnull=False).all().count()
        qtd_faltas_periodo_depois_exclusao = matricula_diario.matricula_periodo.get_total_faltas()

        # regras para verificar situação das faltas e abonos DEPOIS DA EXCLUSÃO de abono
        self.assertEqual(qtd_faltas_diario_antes_exclusao, qtd_faltas_diario_depois_exclusao)
        self.assertEqual(qtd_faltas_periodo_depois_exclusao, qtd_faltas_periodo_antes_exclusao + 1)
        self.assertEqual(qtd_faltas_abonadas_depois_exclusao, qtd_faltas_abonadas_antes_exclusao - 1)

    def acompanhar_aulas(self):
        matricula_diario = self.retornar(MatriculaDiario)
        # acessando salas virtuais
        url = '/edu/disciplinas/'
        response = self.client.get(url)
        self.assertContains(response, 'Disciplinas')
        # acessando uma sala virtual
        url = f'/edu/disciplina/{matricula_diario.diario.id}/'
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Dados do Diário')
        self.assertContains(response, 'Professores')
        self.assertContains(response, 'Local de Aula')
        self.assertContains(response, 'Horário de Aula')
        self.assertContains(response, 'Calendário')
        # acessando os participantes da sala virtual
        response = self.client.get('{}{}'.format(url, '?tab=participantes'))
        self.assertContains(response, 'Carlos Breno Pereira Silva')

    def visualizar_materiais_didaticos(self):
        matricula_diario = self.retornar(MatriculaDiario)
        # acessando salas virtuais
        url = '/edu/disciplinas/'
        response = self.client.get(url)
        self.assertContains(response, 'Disciplinas')
        # acessando uma sala virtual
        url = f'/edu/disciplina/{matricula_diario.diario.id}/'
        # acessando os materiais de aula
        response = self.client.get('{}{}'.format(url, '?tab=materiais'))
        self.assertContains(response, 'Material 01')

    def cadastrar_material_didatico(self):
        # cadastrando um material
        url = '/admin/edu/materialaula/'
        response = self.client.get(url)
        self.assertContains(response, 'Nenhum Material de Aula encontrado.', status_code=200)
        url = '/admin/edu/materialaula/add/'
        count = MaterialAula.objects.all().count()
        data = dict(tipo=1, descricao='Material 01', url='http://google.com.br')
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(MaterialAula.objects.all().count(), count + 1)
        url = '/admin/edu/materialaula/'
        response = self.client.get(url)
        self.assertContains(response, 'Material 01', status_code=200)

    def vincular_material_didatico(self):
        diario = self.retornar(Diario)
        # verificando a existência do link de acesso à página de diários na página principal
        url = '/edu/meus_diarios/'
        response = self.client.get('/')
        self.assertContains(response, url, status_code=200)
        # acessando a página de diários
        self.client.get(f'{url}2013/')
        # acessando pagina dos materiais de aulas do diario
        professor_diario = diario.professordiario_set.all()[0]
        url_ = f'/edu/materiais_diario/{professor_diario.pk}/1/'
        response_ = self.client.get(url_)
        self.assertContains(response_, 'Materiais de Aula do Diário', status_code=200)
        # vincular material de aula a diário
        material_aula = MaterialAula.objects.filter(professor=professor_diario.professor)[0]
        count_ = MaterialDiario.objects.filter(professor_diario=professor_diario).count()
        data_ = dict(materiais_aula=[material_aula.pk])
        response_ = self.client.post(url_, data_)
        self.assert_no_validation_errors(response_)
        self.assertEqual(MaterialDiario.objects.filter(professor_diario=professor_diario).count(), count_ + 1)
        response_ = self.client.get(url_)
        self.assertContains(response_, 'Material vinculado com sucesso', status_code=200)

    def lancar_notas_professor(self, nota=80, etapa=1, descricao_componente=None):
        matricula_diario = None
        if descricao_componente:
            matricula_diario = MatriculaDiario.objects.get(diario__componente_curricular__componente__descricao=descricao_componente)
        else:
            matricula_diario = self.retornar(MatriculaDiario)

            # acessando a página de visualização de diário na aba "Avaliações"
        url = f'/edu/meu_diario/{matricula_diario.diario.pk}/1/?tab=notas'
        self.client.get(url)

        if etapa == 1:
            nota_avaliacao = matricula_diario.get_notas_etapa_1()[0]
            if not nota:
                # lançando uma nota vazia
                url = f'/edu/meu_diario/{matricula_diario.diario.pk}/1/'
                self.client.get(url)
                data = {'lancamento_nota': 1, f'{1};{matricula_diario.pk};{nota_avaliacao.item_configuracao_avaliacao.pk}': ''}
                self.assertIsNotNone(matricula_diario.nota_1)
                response = self.client.post(url, data)
                matricula_diario = MatriculaDiario.objects.get(pk=matricula_diario.pk)
                self.assert_no_validation_errors(response)
                self.assertIsNone(matricula_diario.nota_1)
                self.assertTrue(matricula_diario.is_carga_horaria_diario_fechada())
                self.assertEqual(matricula_diario.get_situacao_frequencia()['rotulo'], 'Aprovado')
                self.assertEqual(matricula_diario.get_situacao_nota()['rotulo'], 'Cursando')
                self.assertEqual(matricula_diario.get_situacao_diario()['rotulo'], 'Cursando')
                self.assertEqual(matricula_diario.get_situacao_registrada_diario()['rotulo'], 'Cursando')
                self.assertFalse(matricula_diario.pode_fechar_periodo_letivo())
                self.assertTrue(matricula_diario.is_cursando())
                self.assertFalse(matricula_diario.realizou_todas_avaliacoes_regulares())
                self.assertFalse(matricula_diario.realizou_todas_avaliacoes())
                self.assertFalse(matricula_diario.is_aprovado_sem_prova_final())
                self.assertFalse(matricula_diario.realizou_avaliacao_final())
                self.assertFalse(matricula_diario.is_em_prova_final())
                self.assertFalse(matricula_diario.is_aprovado_em_prova_final())
                self.assertFalse(matricula_diario.is_aprovado_por_nota())
                self.assertTrue(matricula_diario.is_aprovado_por_frequencia())
                self.assertFalse(matricula_diario.is_aprovado())
                self.assertEqual(matricula_diario.get_media_disciplina(), None)
                self.assertEqual(matricula_diario.get_media_final_disciplina(), None)

            elif nota < matricula_diario.diario.turma.matriz.estrutura.media_evitar_reprovacao_direta:
                # lançando uma nota para aprovar o aluno reprovar direto
                data = {'lancamento_nota': 1, f'{1};{matricula_diario.pk};{nota_avaliacao.item_configuracao_avaliacao.pk}': nota}  # 20
                self.assertIsNone(matricula_diario.nota_1)
                response = self.client.post(url, data)
                matricula_diario = MatriculaDiario.objects.get(pk=matricula_diario.pk)
                self.assert_no_validation_errors(response)
                self.assertTrue(matricula_diario.is_carga_horaria_diario_fechada())
                self.assertEqual(matricula_diario.get_situacao_frequencia()['rotulo'], 'Aprovado')
                self.assertEqual(matricula_diario.get_situacao_nota()['rotulo'], 'Reprovado')
                self.assertEqual(matricula_diario.get_situacao_diario()['rotulo'], 'Reprovado')
                self.assertEqual(matricula_diario.get_situacao_registrada_diario()['rotulo'], 'Cursando')
                self.assertTrue(matricula_diario.pode_fechar_periodo_letivo())
                self.assertTrue(matricula_diario.is_cursando())
                self.assertTrue(matricula_diario.realizou_todas_avaliacoes_regulares())
                self.assertTrue(matricula_diario.realizou_todas_avaliacoes())
                self.assertFalse(matricula_diario.is_aprovado_sem_prova_final())
                self.assertFalse(matricula_diario.realizou_avaliacao_final())
                self.assertFalse(matricula_diario.is_em_prova_final())
                self.assertFalse(matricula_diario.is_aprovado_em_prova_final())
                self.assertFalse(matricula_diario.is_aprovado_por_nota())
                self.assertTrue(matricula_diario.is_aprovado_por_frequencia())
                self.assertFalse(matricula_diario.is_aprovado())
                self.assertEqual(matricula_diario.get_media_disciplina(), nota)
                self.assertEqual(matricula_diario.get_media_final_disciplina(), nota)

            elif nota >= matricula_diario.diario.turma.matriz.estrutura.media_aprovacao_sem_prova_final:
                # lançando uma nota para aprovar o aluno direto
                url = f'/edu/meu_diario/{matricula_diario.diario.pk}/1/'
                self.client.get(url)
                data = {'lancamento_nota': 1, f'{1};{matricula_diario.pk};{nota_avaliacao.item_configuracao_avaliacao.pk}': nota}
                response = self.client.post(url, data)
                matricula_diario = MatriculaDiario.objects.get(pk=matricula_diario.pk)
                self.assertTrue(matricula_diario.is_carga_horaria_diario_fechada())
                self.assertEqual(matricula_diario.get_situacao_frequencia()['rotulo'], 'Aprovado')
                self.assertEqual(matricula_diario.get_situacao_nota()['rotulo'], 'Aprovado')
                self.assertEqual(matricula_diario.get_situacao_diario()['rotulo'], 'Aprovado')
                self.assertEqual(matricula_diario.get_situacao_registrada_diario()['rotulo'], 'Cursando')
                self.assertTrue(matricula_diario.pode_fechar_periodo_letivo())
                self.assertTrue(matricula_diario.is_cursando())
                self.assertTrue(matricula_diario.realizou_todas_avaliacoes_regulares())
                self.assertTrue(matricula_diario.realizou_todas_avaliacoes())
                self.assertTrue(matricula_diario.is_aprovado_sem_prova_final())
                self.assertFalse(matricula_diario.realizou_avaliacao_final())
                self.assertFalse(matricula_diario.is_em_prova_final())
                self.assertFalse(matricula_diario.is_aprovado_em_prova_final())
                self.assertTrue(matricula_diario.is_aprovado_por_nota())
                self.assertTrue(matricula_diario.is_aprovado_por_frequencia())
                self.assertTrue(matricula_diario.is_aprovado())
                self.assertEqual(matricula_diario.get_media_disciplina(), nota)
                self.assertEqual(matricula_diario.get_media_final_disciplina(), nota)

            elif (
                nota >= matricula_diario.diario.turma.matriz.estrutura.media_evitar_reprovacao_direta
                and nota < matricula_diario.diario.turma.matriz.estrutura.media_aprovacao_sem_prova_final
            ):
                # lançando uma nota para levar o aluno para prova final
                url = f'/edu/meu_diario/{matricula_diario.diario.pk}/1/'
                self.client.get(url)
                data = {'lancamento_nota': 1, f'{1};{matricula_diario.pk};{nota_avaliacao.item_configuracao_avaliacao.pk}': nota}  # 50
                response = self.client.post(url, data)
                matricula_diario = MatriculaDiario.objects.get(pk=matricula_diario.pk)
                self.assert_no_validation_errors(response)
                self.assertTrue(matricula_diario.is_carga_horaria_diario_fechada())
                self.assertEqual(matricula_diario.get_situacao_frequencia()['rotulo'], 'Aprovado')
                self.assertEqual(matricula_diario.get_situacao_nota()['rotulo'], 'Prova Final')
                self.assertEqual(matricula_diario.get_situacao_diario()['rotulo'], 'Prova Final')
                self.assertEqual(matricula_diario.get_situacao_registrada_diario()['rotulo'], 'Cursando')
                self.assertFalse(matricula_diario.pode_fechar_periodo_letivo())
                self.assertTrue(matricula_diario.is_cursando())
                self.assertTrue(matricula_diario.realizou_todas_avaliacoes_regulares())
                self.assertFalse(matricula_diario.realizou_todas_avaliacoes())
                self.assertFalse(matricula_diario.is_aprovado_sem_prova_final())
                self.assertFalse(matricula_diario.realizou_avaliacao_final())
                self.assertTrue(matricula_diario.is_em_prova_final())
                self.assertFalse(matricula_diario.is_aprovado_em_prova_final())
                self.assertFalse(matricula_diario.is_aprovado_por_nota())
                self.assertTrue(matricula_diario.is_aprovado_por_frequencia())
                self.assertFalse(matricula_diario.is_aprovado())
                self.assertEqual(matricula_diario.get_media_disciplina(), nota)
                self.assertEqual(matricula_diario.get_media_final_disciplina(), None)

        elif etapa == 5:
            nota_avaliacao = matricula_diario.get_notas_etapa_5()[0]
            if not nota:
                # Retirando a nota da avaliação final
                url = f'/edu/meu_diario/{matricula_diario.diario.pk}/5/'
                self.client.get(url)
                data = {'lancamento_nota': 1, f'{5};{matricula_diario.pk};{nota_avaliacao.item_configuracao_avaliacao.pk}': ''}
                self.client.post(url, data)
                matricula_diario = self.recarregar(matricula_diario)
                self.assertIsNone(matricula_diario.nota_final)

            elif nota >= matricula_diario.diario.turma.matriz.estrutura.media_aprovacao_avaliacao_final:
                # lançando uma nota para aprovar o aluno na avaliação final
                url = f'/edu/meu_diario/{matricula_diario.diario.pk}/5/'
                self.client.get(url)
                data = {'lancamento_nota': 1, f'{5};{matricula_diario.pk};{nota_avaliacao.item_configuracao_avaliacao.pk}': nota}  # 80
                response = self.client.post(url, data)
                matricula_diario = MatriculaDiario.objects.get(pk=matricula_diario.pk)
                self.assert_no_validation_errors(response)
                self.assertIsNotNone(matricula_diario.nota_1)
                self.assertTrue(matricula_diario.is_carga_horaria_diario_fechada())
                self.assertEqual(matricula_diario.get_situacao_frequencia()['rotulo'], 'Aprovado')
                self.assertEqual(matricula_diario.get_situacao_nota()['rotulo'], 'Aprovado')
                self.assertEqual(matricula_diario.get_situacao_diario()['rotulo'], 'Aprovado')
                self.assertEqual(matricula_diario.get_situacao_registrada_diario()['rotulo'], 'Cursando')
                self.assertTrue(matricula_diario.pode_fechar_periodo_letivo())
                self.assertTrue(matricula_diario.is_cursando())
                self.assertTrue(matricula_diario.realizou_todas_avaliacoes_regulares())
                self.assertTrue(matricula_diario.realizou_todas_avaliacoes())
                self.assertFalse(matricula_diario.is_aprovado_sem_prova_final())
                self.assertTrue(matricula_diario.realizou_avaliacao_final())
                self.assertTrue(matricula_diario.is_em_prova_final())
                self.assertTrue(matricula_diario.is_aprovado_em_prova_final())
                self.assertTrue(matricula_diario.is_aprovado_por_nota())
                self.assertTrue(matricula_diario.is_aprovado_por_frequencia())
                self.assertTrue(matricula_diario.is_aprovado())
                self.assertEqual(matricula_diario.get_media_disciplina(), matricula_diario.nota_1)
                self.assertEqual(matricula_diario.get_media_final_disciplina(), nota)
                # Voltando a nota para aprovar o aluno direto
                response = self.client.post(url, data)
                self.assert_no_validation_errors(response)
                matricula_diario = self.recarregar(matricula_diario)
                self.assertIsNotNone(matricula_diario.nota_1)
                self.assertIsNotNone(matricula_diario.nota_final)
            else:
                # TODO Reprovado na prova final
                pass

        # visualizando a mensagem de registro de notas
        url = f'/edu/meu_diario/{matricula_diario.diario.pk}/1/'
        response = self.client.get(url)
        self.assertContains(response, url, status_code=200)
        self.assertContains(response, 'Notas registradas com sucesso')

    def alterar_configuracao_avaliacao(self):
        matricula_diario = self.retornar(MatriculaDiario)
        nota_avaliacao = matricula_diario.get_notas_etapa_1()[0]

        # acessando meu diário
        url = f'/edu/meu_diario/{matricula_diario.diario.pk}/1/'
        response = self.client.get(url)
        self.assertContains(response, url, status_code=200)

        for k, v in ConfiguracaoAvaliacao.FORMA_CALCULO_CHOICES:
            nota_final = None

            itens = [
                {'tipo': ItemConfiguracaoAvaliacao.TIPO_PROVA, 'sigla': 'T1', 'nota_maxima': 100},
                {'tipo': ItemConfiguracaoAvaliacao.TIPO_PROVA, 'sigla': 'T2', 'nota_maxima': 100},
            ]
            if v == 'Média Aritmética':
                nota1 = 60
                nota2 = 100
                nota_final = 80
                divisor = None
            elif v == 'Soma Simples':
                itens[0].update({'nota_maxima': 50})
                itens[1].update({'nota_maxima': 50})
                nota1 = 40
                nota2 = 50
                nota_final = 90
                divisor = None
            elif v == 'Média Ponderada':
                peso1 = 65
                peso2 = 35
                itens[1].update({'peso': peso1})
                itens[0].update({'peso': peso2})
                nota1 = 80
                nota2 = 60
                divisor = None
                nota_final = ((nota1 * peso1) + (nota2 * peso2)) / (peso1 + peso2)
            elif v == 'Soma com Divisor Informado':
                nota1 = 70
                nota2 = 80
                divisor = 2
                nota_final = 75
            elif v == 'Maior Nota':
                nota1 = 73
                nota2 = 72
                nota_final = 73
                divisor = None

            if nota_final:

                # removendo as notas lançadas anteriormente
                url = f'/edu/meu_diario/{matricula_diario.diario.pk}/1/'
                response = self.client.get(url)
                notas_avaliacao = matricula_diario.get_notas_etapa_1()
                data = {'lancamento_nota': 1}
                for nota_avaliacao in notas_avaliacao:
                    data[f'{1};{matricula_diario.pk};{nota_avaliacao.item_configuracao_avaliacao.pk}'] = ('',)
                response = self.client.post(url, data)

                # atualizando a configuração avaliação
                configuracao_avaliacao_antes = ConfiguracaoAvaliacao.objects.all().count()
                self.atualizar_configuracao_avaliacao(nota_avaliacao.item_configuracao_avaliacao.configuracao_avaliacao, forma_calculo=k, itens=itens, divisor=divisor)

                configuracao_avaliacao_depois = ConfiguracaoAvaliacao.objects.all().count()
                self.assertEqual(configuracao_avaliacao_depois, configuracao_avaliacao_antes)

                matricula_diario = self.retornar(MatriculaDiario)
                self.assertIsNone(matricula_diario.nota_1)

                url = f'/edu/meu_diario/{matricula_diario.diario.pk}/1/'
                response = self.client.get(url)
                notas_avaliacao = matricula_diario.get_notas_etapa_1()
                data = {
                    'lancamento_nota': 1,
                    f'{1};{matricula_diario.pk};{notas_avaliacao[0].item_configuracao_avaliacao.pk}': nota1,
                    f'{1};{matricula_diario.pk};{notas_avaliacao[1].item_configuracao_avaliacao.pk}': nota2,
                }
                response = self.client.post(url, data)

                self.assert_no_validation_errors(response)

                matricula_diario = self.retornar(MatriculaDiario)
                # TODO parou de funcionar no django 1.9 com sqlite
                # self.assertEqual(matricula_diario.nota_1, nota_final)

    def imprimir_diario(self):
        diario = self.retornar(Diario)
        # acessando a página de impressão de boletim do diário
        url = f'/edu/emitir_boletins_pdf/{diario.pk}/?html=1'
        response = self.client.get(url)
        self.assertContains(response, 'BOLETIM DE NOTAS DO DIÁRIO', status_code=200)
        # acessando a página de impressão da relação de alunos
        url = f'/edu/relacao_alunos_pdf/{diario.pk}/?html=1'
        response = self.client.get(url)
        self.assertContains(response, 'RELAÇÃO DE ALUNOS', status_code=200)
        # acessando a página de impressão de diário para a etapa 1
        url = f'/edu/diario_pdf/{diario.pk}/1/?html=1'
        response = self.client.get(url)
        self.assertContains(response, 'REGISTRO DE ATIVIDADES', status_code=200)

    def visualizar_boletim_individual(self):
        aluno = self.retornar(Aluno)
        # acessando o boletim
        url = f'/edu/emitir_boletim_pdf/{aluno.get_ultima_matricula_periodo().id}/?html=1'
        response = self.client.get(url)
        self.assertContains(response, 'BOLETIM DE NOTAS INDIVIDUAL')

    def entregar_etapa(self, etapa=1):
        matricula_diario = self.retornar(MatriculaDiario)
        # entregando a etapa
        url = f'/edu/entregar_etapa/{matricula_diario.diario.pk}/{etapa}/'
        data = {'zerar_notas': False}
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Etapa entregue com sucesso.')
        matricula_diario = self.recarregar(matricula_diario)
        self.assertEqual(getattr(matricula_diario.diario, f'posse_etapa_{etapa}'), Diario.POSSE_REGISTRO_ESCOLAR)

    def lancar_notas_secretario(self, nota='', etapa=1):
        matricula_diario = self.retornar(MatriculaDiario)
        nota_avaliacao = matricula_diario.get_notas_etapa_1()[0]
        # acessando a página de visualização de diário na aba "Lançamento de Notas/Faltas"
        url = f'/edu/diario/{matricula_diario.diario.pk}/?tab=notas_faltas'
        data = {'lancamento_nota': 1, f'{etapa};{matricula_diario.pk};{nota_avaliacao.item_configuracao_avaliacao.pk}': nota}
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)

    def alterar_aulas_faltas_notas(self):
        matricula_diario = self.retornar(MatriculaDiario)
        nota_avaliacao = matricula_diario.get_notas_etapa_1()[0]
        # acessando a página de visualização de diário na aba "Lançamento de Notas/Faltas"
        url = f'/edu/diario/{matricula_diario.diario.pk}/?tab=notas_faltas'
        response = self.client.get(url)
        self.assertContains(response, f'Diário ({matricula_diario.diario.pk}) - {matricula_diario.diario.componente_curricular.componente.sigla}', status_code=200)
        # tranferindo a posse do diário do professor para o registro escolar
        url = f'/edu/transferir_posse_diario/{matricula_diario.diario.pk}/{1}/{Diario.POSSE_REGISTRO_ESCOLAR}/'
        self.client.get(url)
        url = f'/edu/diario/{matricula_diario.diario.pk}/?tab=notas_faltas'
        response = self.client.get(url)
        self.assertContains(response, 'Posse transferida com sucesso.')
        # acessando a página de listagem de aulas cadastradas para a etapa 1
        url = f'/edu/registrar_chamada/{matricula_diario.diario.pk}/1/'
        self.assertContains(response, url)
        self.client.get(url)
        # acessando a página de cadastro de aula
        aula = self.retornar(Aula)
        url = f'/edu/adicionar_aula_diario/{matricula_diario.diario.pk}/1/{aula.pk}/'
        self.client.get(url)
        # atualizando uma aula
        data = dict(professor_diario=aula.professor_diario.pk, etapa='1', tipo=1, quantidade=aula.quantidade, data='01/01/2013', conteudo=aula.conteudo)
        self.assertEqual(matricula_diario.diario.get_horas_aulas_etapa_1(), 10)
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        temp = Diario.locals.get(pk=matricula_diario.diario.pk)
        self.assertEqual(temp.get_horas_aulas_etapa_1(), 10)

        # acessando a página de visualização de diário na aba "Lançamento de Notas/Faltas"
        url = f'/edu/diario/{matricula_diario.diario.pk}/?tab=notas_faltas'
        self.client.get(url)
        # lançando a mesma nota definida pelo professor para a etapa 1
        data = {'lancamento_nota': 1, f'{1};{matricula_diario.pk};{nota_avaliacao.item_configuracao_avaliacao.pk}': matricula_diario.nota_1}
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        matricula_diario = MatriculaDiario.locals.get(pk=matricula_diario.pk)
        self.assertIsNotNone(matricula_diario.nota_1)

    def solicitar_relancamento_etapa(self):
        matricula_diario = self.retornar(MatriculaDiario)
        professor_diario = self.retornar(ProfessorDiario)
        # solicitando relançamento da etapa 1
        numero_solicitacao_antes = SolicitacaoUsuario.objects.count()
        numero_solicitacao_relancamento_antes = SolicitacaoRelancamentoEtapa.objects.count()
        url = f'/edu/solicitar_relancamento_etapa/{professor_diario.pk}/{matricula_diario.diario.pk}/'
        data = {'motivo': 'Motivo de Teste.'}
        self.client.post(url, data)
        numero_solicitacao_depois = SolicitacaoUsuario.objects.count()
        numero_solicitacao_relancamento_depois = SolicitacaoRelancamentoEtapa.objects.count()
        self.assertEqual(numero_solicitacao_relancamento_depois, numero_solicitacao_relancamento_antes + 1)
        self.assertEqual(numero_solicitacao_depois, numero_solicitacao_antes + 1)
        self.assertEqual(SolicitacaoRelancamentoEtapa.objects.order_by('-id').all()[0].solicitante.username, professor_diario.professor.vinculo.user.username)

    def indeferir_solicitacao_relancamento_etapa(self):
        # indeferindo a solicitacao de relançamento de etapa
        url = '/admin/edu/solicitacaousuario/'
        self.client.get(url)
        solicitacao = self.retornar(SolicitacaoRelancamentoEtapa)
        url = f'/edu/rejeitar_solicitacao/{solicitacao.pk}/'
        self.client.get(url)
        data = {'razao_indeferimento': 'Fora de prazo.'}
        self.client.post(url, data)
        solicitacao = self.recarregar(solicitacao)
        self.assertEqual(solicitacao.avaliador.username, self.servidor_b.matricula)
        self.assertFalse(solicitacao.atendida)

    def deferir_solicitacao_relancamento_etapa(self):
        # deferindo a solicitação
        solicitacao = self.retornar(SolicitacaoRelancamentoEtapa)
        url = f'/edu/solicitacaousuario/{solicitacao.pk}/?atender=1'
        response = self.client.get(url)
        self.assert_no_validation_errors(response)
        solicitacao = self.recarregar(solicitacao)
        self.assertEqual(solicitacao.avaliador.username, self.servidor_b.matricula)
        self.assertTrue(solicitacao.atendida)

    def fechar_periodo(self, forcar_fechamento, situacao_matricula, situacao_matricula_periodo, situacao_diario, componentes_situacoes=None):
        matricula_diario = self.retornar(MatriculaDiario)
        # acessando a página de fechamento de período letivo
        url = '/edu/fechar_periodo_letivo/'
        self.client.get(url)
        data = dict(
            ano_letivo=matricula_diario.matricula_periodo.ano_letivo.pk,
            periodo_letivo=matricula_diario.matricula_periodo.periodo_letivo,
            tipo="MATRICULA",
            aluno=matricula_diario.matricula_periodo.aluno.pk,
        )
        response = self.client.get(url, data)
        self.assert_no_validation_errors(response)
        self.assertContains(response, matricula_diario.matricula_periodo.aluno.matricula)
        if forcar_fechamento:
            data.update(dict(confirmado='on', forcar_fechamento='on'))
        else:
            data.update(dict(confirmado='on'))
        response = self.client.get(url, data, follow=True)
        self.assert_no_validation_errors(response)
        matricula_diario = self.recarregar(matricula_diario)
        self.assertEqual(matricula_diario.matricula_periodo.aluno.situacao.pk, situacao_matricula)
        self.assertEqual(matricula_diario.matricula_periodo.situacao.pk, situacao_matricula_periodo)

        self.assertContains(response, '100')

        if componentes_situacoes:
            for componente, situacao in list(componentes_situacoes.items()):
                matricula_diario = MatriculaDiario.objects.get(diario__componente_curricular__componente__descricao=componente)
                self.assertEqual(matricula_diario.situacao, situacao)
        else:
            self.assertEqual(matricula_diario.situacao, situacao_diario)

        return response

    def abrir_periodo(self):
        matricula_diario = self.retornar(MatriculaDiario)
        # Reabrindo o período
        # acessando a página de reabertura de período letivo
        url = '/edu/abrir_periodo_letivo/'
        self.client.get(url)
        data = dict(
            ano_letivo=matricula_diario.matricula_periodo.ano_letivo.pk,
            periodo_letivo=matricula_diario.matricula_periodo.periodo_letivo,
            tipo="MATRICULA",
            aluno=matricula_diario.matricula_periodo.aluno.pk,
        )
        response = self.client.get(url, data)
        self.assert_no_validation_errors(response)
        # self.assertContains(response, matricula_diario.matricula_periodo.aluno.matricula)
        # abrindo período letivo
        data.update(dict(confirmado='on'))
        response = self.client.get(url, data, follow=True)
        matricula_diario = self.recarregar(matricula_diario)
        self.assert_no_validation_errors(response)
        # self.assertContains(response, u'100%')

        url = '{}?continue=1'.format(response.request['PATH_INFO'])
        response = self.client.get(url, follow=True)
        self.assert_no_validation_errors(response)
        self.assertEqual(matricula_diario.matricula_periodo.aluno.situacao.pk, SituacaoMatricula.MATRICULADO)

    def configurar_livro(self):
        aluno = self.retornar(Aluno)
        data = dict(
            descricao='Livro 1',
            uo=aluno.curso_campus.diretoria.setor.uo.id,
            modalidades=[aluno.curso_campus.modalidade.id],
            numero_livro=1,
            folhas_por_livro=1,
            numero_folha=1,
            numero_registro=1,
        )
        return self.cadastrar(ConfiguracaoLivro, data)

    def cadastrar_processo(self):
        aluno = self.retornar(Aluno)
        # Cadastrando processo e configuracao de livro
        data = dict(
            vinculo_cadastro=self.servidor_a.get_vinculo(),
            uo=aluno.curso_campus.diretoria.setor.uo,
            setor_origem=aluno.curso_campus.diretoria.setor,
            numero_processo='23057.003498.2009-59',
            assunto='Processo',
            tipo=1,
            palavras_chave='Processo',
        )
        Processo.objects.get_or_create(**data)

    def emitir_diploma(self):
        # Emitir diploma
        aluno = self.retornar(Aluno)
        processo = self.retornar(Processo)
        # Acessando a tela de emissão de diploma
        url = '/edu/emitir_diploma/'
        response = self.client.get(url)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Seleção do Aluno')
        # Primeiro passo do wizard - Selecionando o aluno concluido
        data = dict(aluno=aluno.pk)
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Dados da Emissão')
        # Segundo passo do wizard - Selecionando o processo e emitindo o diploma
        data.update(processo=processo.pk, numero_formulario='12', numero_pasta='23', autenticacao_sistec='XXXXXX')
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Registro de emissão de diploma cadastrado com sucesso')

        self.acessar_como_administrador()
        # acessando admin de registro de emissao de diplomas
        url = '/admin/edu/registroemissaodiploma/'
        response = self.client.get(url)
        self.assertContains(response, aluno.pessoa_fisica.nome, status_code=200)
        self.acessar_como_secretario()

        registro_emissao = self.retornar(RegistroEmissaoDiploma)
        url = f'/edu/registroemissaodiploma/{registro_emissao.id}/?registrar=1'
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Diploma registrado com sucesso')

    def emitir_diploma_lote(self):
        # Emitir diploma

        # selecionando uma turma
        turma = self.retornar(Turma)
        url = '/edu/emitir_diplomas/'
        # Acessando a tela de emissão de diploma
        response = self.client.get(url)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Seleção da Turma')
        # Primeiro passo do wizard - Selecionando a turma
        data = dict(turma=turma.pk)
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        # verificando se existe alunos para a turma selecionada
        self.assertContains(response, 'Seleção dos Alunos')

        matricula_periodo = turma.matriculaperiodo_set.all()[0]

        processo = self.retornar(Processo)
        # Segundo passo do wizard - Selecionando o aluno concluido
        data.update(alunos=tuple([matricula_periodo.aluno.pk]))
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Dados da Emissão')

        # Terceiro passo do wizard - Selecionando o processo e emitindo o diploma
        data.update(processo=processo.pk, numero_formulario='12', prefixo='PASTA', numero_pasta='23')
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Registros de emissão de diploma cadastrados com sucesso.')

        registro_emissao = self.retornar(RegistroEmissaoDiploma)
        url = f'/edu/registroemissaodiploma/{registro_emissao.id}/?registrar=1'
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Diploma registrado com sucesso')

    def imprimir_registro_emissao_diploma(self):
        # Acessando o registro de emissão de diplomas
        registro_emissao = self.retornar(RegistroEmissaoDiploma)
        url = f'/edu/registroemissaodiploma/{registro_emissao.id}/'
        response = self.client.get(url)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Cancelar')
        self.assertEqual(registro_emissao.cancelado, False)
        # Cancelando emissão do diploma
        url = f'/edu/cancelar_registroemissaodiploma/{registro_emissao.id}/'
        data = dict(motivo_cancelamento='Erro de emissão')
        response = self.client.post(url, data, follow=True)
        registro_emissao = RegistroEmissaoDiploma.objects.get(id=registro_emissao.id)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Registro de emissão de diploma cancelado com sucesso.')
        self.assertEqual(registro_emissao.cancelado, True)

    def visualizar_historico(self, final=False):
        # acessando o histórico
        aluno = self.retornar(Aluno)
        if final:
            url = f'/edu/emitir_historico_final_pdf/{aluno.id}/?html=1'
        else:
            url = f'/edu/emitir_historico_parcial_pdf/{aluno.id}/?html=1'
        response = self.client.get(url)
        self.assertContains(response, 'HISTÓRICO ESCOLAR')

    def procedimento_matricula(self, situacao_desejada):
        aluno = self.retornar(Aluno)
        opcoes = None
        url = None

        if situacao_desejada == SituacaoMatricula.CANCELAMENTO_COMPULSORIO:
            opcoes = '20;23;7'
            url = '/edu/realizar_cancelamento_matricula/{}/'
        elif situacao_desejada == SituacaoMatricula.CANCELADO:
            opcoes = '10;4;7'
            url = '/edu/realizar_cancelamento_matricula/{}/'
        elif situacao_desejada == SituacaoMatricula.CANCELAMENTO_POR_DESLIGAMENTO:
            opcoes = '97;97;7'
            url = '/edu/realizar_cancelamento_matricula/{}/'
        elif situacao_desejada == SituacaoMatricula.CANCELAMENTO_POR_DUPLICIDADE:
            opcoes = '98;98;7'
            url = '/edu/realizar_cancelamento_matricula/{}/'
        elif situacao_desejada == SituacaoMatricula.EVASAO:
            opcoes = '9;15;7'
            url = '/edu/realizar_cancelamento_matricula/{}/'
        elif situacao_desejada == SituacaoMatricula.JUBILADO:
            opcoes = '3;14;7'
            url = '/edu/realizar_cancelamento_matricula/{}/'
        elif situacao_desejada == SituacaoMatricula.INTERCAMBIO:
            opcoes = '17;24;6'
            url = '/edu/realizar_trancamento_matricula/{}/'
        elif situacao_desejada == SituacaoMatricula.TRANCADO:
            opcoes = '2;3;6'
            url = '/edu/realizar_trancamento_matricula/{}/'
        elif situacao_desejada == SituacaoMatricula.TRANCADO_VOLUNTARIAMENTE:
            opcoes = '99;99;6'
            url = '/edu/realizar_trancamento_matricula/{}/'

        url = url.format(aluno.get_ultima_matricula_periodo().id)

        # acessando o formulário
        response = self.client.get(url)
        self.assertContains(response, 'ar Matrícula', status_code=200)

        # realizando o procedimento
        processo = self.retornar(Processo)
        data = dict(processo=processo.pk, data='31/05/2014', opcoes=opcoes, motivo='.')
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)

        # verificando se realmente funcionou
        aluno = self.recarregar(aluno)
        self.assertEqual(situacao_desejada, aluno.situacao.id)

    def desfazer_ultimo_procedimento_matricula(self):
        aluno = self.retornar(Aluno)
        procedimento_matricula = self.retornar(ProcedimentoMatricula)

        url = f'{aluno.get_absolute_url()}?tab=procedimentos&procedimento_id={procedimento_matricula.pk}'
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Procedimento desfeito com sucesso!', status_code=200)

        # testando se situação voltou
        aluno = self.recarregar(aluno)
        self.assertEqual(procedimento_matricula.situacao_matricula_anterior, aluno.situacao)

    def pc_reintegracao(self, ano_letivo, periodo_letivo):
        # acessando o form de reintegração
        aluno = self.retornar(Aluno)
        ultimo_procedimento = self.retornar(ProcedimentoMatricula)
        situacao_anterior = ultimo_procedimento.situacao_matricula_anterior.id
        url = f'/edu/reintegrar_aluno/{aluno.get_ultima_matricula_periodo().pk}/'
        response = self.client.get(url)
        self.assertContains(response, 'Reintegrar Aluno', status_code=200)

        # realizando a reintegração
        processo = self.retornar(Processo)
        data = dict(processo=processo.pk, data='01/06/2014', motivo='Foi solicitado pelo aluno.', ano_letivo=ano_letivo.id, periodo_letivo=periodo_letivo)
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        # verificando se realmente reintegrou o aluno
        aluno = self.recarregar(aluno)
        self.assertEqual(situacao_anterior, aluno.situacao.id)

    def cadastrar_polo(self, **params):
        """
        Cria um polo com valores padrões caso não seja passado parâmetro
        """

        url = '/admin/edu/polo/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Polo EAD', status_code=200)
        count = Polo.objects.all().count()
        init = dict(
            descricao='Polo Padrão',
            sigla='PP',
            cidade=self.retornar(Cidade).pk,
            estrutura_disponivel='Básica',
            logradouro='Rua Qualquer',
            numero='70',
            complemento='',
            bairro='Tirol',
            cep='58071100',
            do_municipio=False,
            diretoria=self.retornar(Diretoria).pk,
            telefone_principal='8422222222',
            telefone_secundario='8432333333',
        )

        init.update({'horariofuncionamentopolo_set-TOTAL_FORMS': '0', 'horariofuncionamentopolo_set-INITIAL_FORMS': '0', 'horariofuncionamentopolo_set-MAX_NUM_FORMS': '1000'})

        init.update(params)
        response = self.client.post(url, init)
        self.assert_no_validation_errors(response)
        self.assertEqual(Polo.objects.all().count(), count + 1)
        return Polo.objects.all().order_by('-id')[0]

    def acessar_polo(self):
        polo = self.retornar(Polo)
        url = f'/edu/polo/{polo.id}/'
        response = self.client.get(url)
        self.assertContains(response, polo.descricao, status_code=200)

    def cadastrar_atividade_polo(self, **params):
        """
        Cria uma atividade do polo com valores padrões caso não seja passado parâmetro
        """

        url = '/admin/edu/atividadepolo/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Atividade do Polo', status_code=200)
        count = AtividadePolo.objects.all().count()
        init = dict(
            polo=self.retornar(Polo).id,
            nome='Atividade 1',
            descricao='Faça uma atividade valendo nota.',
            sala=self.retornar(Sala).id,
            data_inicio='11/06/2013',
            data_fim='12/06/2013',
        )

        init.update(params)
        response = self.client.post(url, init)
        self.assert_no_validation_errors(response)
        self.assertEqual(AtividadePolo.objects.all().count(), count + 1)
        return AtividadePolo.objects.all().order_by('-id')[0]

    def cadastrar_estrutura_curso(self, **params):
        """
        Cria uma estrutura de curso com valores padrões caso não seja passado parâmetro
        """

        url = '/admin/edu/estruturacurso/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Estrutura', status_code=200)
        count = EstruturaCurso.objects.all().count()
        init = dict(
            descricao='PRONATEC / FICs 75%',
            tipo_avaliacao=EstruturaCurso.TIPO_AVALIACAO_FIC,
            limite_reprovacao='0',
            qtd_minima_disciplinas='0',
            criterio_avaliacao=EstruturaCurso.CRITERIO_AVALIACAO_NOTA,
            media_aprovacao_sem_prova_final='70',
            media_evitar_reprovacao_direta='50',
            media_aprovacao_avaliacao_final='70',
            percentual_frequencia='75',
            ira=EstruturaCurso.IRA_ARITMETICA_NOTAS_FINAIS,
            numero_disciplinas_superior_periodo='2',
            qtd_periodos_conclusao=0,
            qtd_max_reprovacoes_periodo=0,
            qtd_max_reprovacoes_disciplina=0,
            percentual_max_aproveitamento=0,
            numero_max_certificacoes=0,
            media_certificacao_conhecimento=0,
        )
        init.update({'representacaoconceitual_set-TOTAL_FORMS': '0', 'representacaoconceitual_set-INITIAL_FORMS': '0', 'representacaoconceitual_set-MAX_NUM_FORMS': '1000'})
        init.update(params)
        response = self.client.post(url, init)
        self.assert_no_validation_errors(response)
        self.assertEqual(EstruturaCurso.objects.all().count(), count + 1)

        # acessando a estrutura
        estrutura_curso = self.retornar(EstruturaCurso)
        url = f'/edu/estruturacurso/{estrutura_curso.id}/'
        response = self.client.get(url)
        self.assertContains(response, estrutura_curso.descricao, status_code=200)

        return estrutura_curso

    def cadastrar_matriz(self, **params):
        """
        cria uma matriz curricular com valores padrões caso não seja passado o parâmetro
        """
        url = '/admin/edu/matriz/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Matriz Curricular', status_code=200)
        nivel_ensino_pk = params.get('nivel_ensino')
        if not nivel_ensino_pk:
            nivel_ensino_pk = self.retornar(NivelEnsino).pk
        count = Matriz.objects.all().count()
        init = dict(
            descricao='Mestrado em Agricultor Familiar',
            ano_criacao=self.ano_2013.pk,
            periodo_criacao='1',
            data_inicio='11/06/2013',
            data_fim='',
            ativo='on',
            nivel_ensino=nivel_ensino_pk,
            qtd_periodos_letivos='3',
            ch_componentes_obrigatorios='20',
            ch_componentes_optativos='0',
            ch_componentes_eletivos='0',
            ch_seminarios='0',
            ch_componentes_tcc='10',
            ch_pratica_profissional='0',
            ch_atividades_complementares='0',
            ch_atividades_aprofundamento='0',
            ch_atividades_extensao='0',
            ch_pratica_como_componente='0',
            ch_visita_tecnica='0',
        )
        init.update(params)
        response = self.client.post(url, init)
        self.assert_no_validation_errors(response)
        self.assertEqual(Matriz.objects.all().count(), count + 1)

        # acessando a matriz
        matriz = self.retornar(Matriz)
        url = f'/edu/matriz/{matriz.id}/'
        response = self.client.get(url)
        self.assertContains(response, matriz.descricao, status_code=200)

        return matriz

    def cadastrar_componente_curricular(self, tipo_componente, **params):
        url = '/admin/edu/componente/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Componente', status_code=200)
        count = Componente.objects.all().count()
        diretoria_pk = params.get('diretoria')
        nivel_ensino_pk = params.get('nivel_ensino')
        if not diretoria_pk:
            diretoria_pk = self.retornar(Diretoria).pk
        if not nivel_ensino_pk:
            nivel_ensino_pk = self.retornar(NivelEnsino).pk
        init = dict(
            descricao='Administração da propriedade rural',
            descricao_historico='Administração da propriedade rural',
            abreviatura='ADMPR',
            tipo=tipo_componente.pk,
            diretoria=diretoria_pk,
            nivel_ensino=nivel_ensino_pk,
            ch_hora_relogio='10',
            ch_hora_aula='10',
            ch_qtd_creditos='10',
        )
        init.update(params)
        response = self.client.post(url, init)
        componente = self.retornar(Componente)
        count_tipo = Componente.objects.filter(tipo=componente.tipo).count()
        self.assert_no_validation_errors(response)
        self.assertEqual(Componente.objects.all().count(), count + 1)
        self.assertEqual(componente.sigla, f'{tipo_componente}.000{str(count_tipo)}')

        # acessando o componente curricular
        url = f'/edu/componente/{componente.id}/'
        response = self.client.get(url)
        self.assertContains(response, componente.descricao, status_code=200)

        return componente

    def vincular_componente(self, matriz, componente, **params):
        nucleo_pk = params.get('nucleo')
        if not nucleo_pk:
            nucleo_pk = self.retornar(Nucleo)
        # vinculando Componente A à matriz no primeiro periodo
        url = f'/edu/vincular_componente/{matriz.pk}/'
        response = self.client.get(url)
        self.assertContains(response, 'Vincular Componente de matriz', status_code=200)
        count = matriz.componentecurricular_set.count()
        init = dict(matriz=matriz.pk, componente=componente.pk, tipo='1', qtd_avaliacoes='1', nucleo=nucleo_pk, ch_presencial='10', ch_pratica='0', ch_extensao='0', percentual_maximo_ead='0', ch_pcc=0, ch_visita_tecnica=0)
        init.update(params)
        response = self.client.post(url, init)
        self.assert_no_validation_errors(response)
        self.assertEqual(matriz.componentecurricular_set.count(), count + 1)

    def cadastrar_curso(self, data):
        # acessando a página de cadastro de curso
        url = '/admin/edu/cursocampus/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Curso', status_code=200)
        count = CursoCampus.locals.all().count()
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(CursoCampus.locals.all().count(), count + 1)
        return self.retornar(CursoCampus)

    def definindo_horario_diario(self, dias_semana=[], descricao_componente=None):
        diario = None
        if descricao_componente:
            diario = Diario.objects.filter(componente_curricular__componente__descricao=descricao_componente).order_by('-id')[0]
        else:
            diario = self.retornar(Diario)

        url = f'/edu/diario/{diario.pk}/'
        response = self.client.get(url)
        # localizando o link de acesso à página de e definição de horário
        url = f'/edu/definir_horario_aula_diario/{diario.pk}/'
        self.assertContains(response, url)
        # acessando a página de definição de horário
        response = self.client.get(url)
        self.assertContains(response, 'Definir Horário de Aula', status_code=200)
        self.assertEqual(diario.horarioauladiario_set.filter(dia_semana__in=dias_semana).count(), 0)
        horario_campus = diario.horario_campus
        horarios_aulas = horario_campus.horarioaula_set.all().order_by('-id')

        horarios = []
        # mantendo os horarios salvos previamente
        for horario_aula_diario in diario.horarioauladiario_set.all():
            horarios.append(f'{horario_aula_diario.horario_aula.pk};{horario_aula_diario.dia_semana}')
        # add horarios nos dias_semana passado
        for dia_semana in dias_semana:
            for i in range(0, 3):
                horarios.append(f'{horarios_aulas[i].pk};{dia_semana}')

        data = dict(horario=horarios)

        response = self.client.post(f'/edu/definir_horario_aula_diario/{diario.pk}/', data, follow=True)
        self.assertContains(response, 'Horário definido com sucesso', status_code=200)

        for dia_semana in dias_semana:
            dia_semana += 1
            self.assertTrue(f'{dia_semana}M123' in diario.get_horario_aulas())

    def enviar_mensagem(self):
        # acessando url para envio de mensagem
        url = '/edu/enviar_mensagem/'
        response = self.client.get(url)
        self.assertContains(response, 'Nova Mensagem', status_code=200)

        # contando mensagens enviadas
        numero_mensagens_antes = Mensagem.objects.count()

        # selecionando uma turma para envio de mensagem
        turma = self.retornar(Turma)
        aluno = self.retornar(Aluno)
        data = dict(alunos=aluno.pk, turma=turma.pk, via_suap=True)
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)

        self.assertContains(response, aluno.matricula)
        data.update(dict(assunto='Assunto da menssagem', conteudo='Conteúdo da mensagem', confirmacao='on'))

        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'enviadas com sucesso')

        # verificando a mensagem foi persistida
        numero_mensagens_depois = Mensagem.objects.count()
        self.assertEqual(numero_mensagens_depois, numero_mensagens_antes + 1)

        # acessando a caixa de saida
        url = '/admin/edu/mensagemsaida/'
        response = self.client.get(url)
        self.assertContains(response, 'Assunto da menssagem', status_code=200)

    def caixa_entrada_aluno(self):
        # acessando url
        url = '/'
        response = self.client.get(url)
        self.assertContains(response, 'Mensagem', status_code=200)
        self.assertContains(response, 'Não lida', status_code=200)

        # acessando caixa de entrada como aluno
        url = '/admin/edu/mensagementrada/'
        response = self.client.get(url)
        self.assertContains(response, 'Mensagens Recebidas', status_code=200)

        # acessando uma mensagem
        mensagem = self.retornar(Mensagem)
        url = f'/edu/mensagem/{mensagem.pk}/'
        response = self.client.get(url)
        self.assertContains(response, 'Assunto da menssagem', status_code=200)


class FicTestCase(EduTestCase):
    def setUp(self):
        super().setUp()
        self.initial_data['FormaIngresso'] = self.retornar(FormaIngresso, chaves={'descricao': 'Matrícula Direta'})
        self.initial_data['NivelEnsino'] = NivelEnsino.objects.get(pk=NivelEnsino.FUNDAMENTAL)
        self.initial_data['TipoComponente'] = self.retornar(TipoComponente, chaves={'descricao': 'FIC'})
        self.initial_data['Componente'] = self.retornar(Componente, chaves={'sigla': 'FIC.0001'})
        self.initial_data['Matriz'] = self.retornar(Matriz, chaves={'descricao': 'FIC em Agricultor Familiar [PRONATEC]'})
        self.initial_data['CursoCampus'] = self.retornar(CursoCampus, chaves={'descricao': 'FIC+ Agricultor Familiar [PRONATEC]'})
        self.initial_data['MatrizCurso'] = self.retornar(MatrizCurso, chaves={'matriz__descricao': 'FIC em Agricultor Familiar [PRONATEC]'})
        self.initial_data['Professor'] = self.retornar(Professor)

    def efetuar_matricula_turma(self):
        aluno = self.retornar(Aluno)
        numero_matriculas_diario_antes = MatriculaDiario.objects.count()
        url = f'/edu/efetuar_matricula_turma/{aluno.pk}/'
        response = self.client.get(url)
        self.assertContains(response, 'Matrícula em Turma', status_code=200)
        turma = self.retornar(Turma)
        data = dict(turma=turma.pk)
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        numero_matriculas_diario_depois = MatriculaDiario.objects.count()
        self.assertEqual(numero_matriculas_diario_depois, numero_matriculas_diario_antes + turma.diario_set.count())

    def test_fluxo(self):
        # VINCULAÇÃO DOS USUÁRIOS
        self.vincular_usuario_a_diretoria('Secretário Acadêmico')

        # EAD
        self.acessar_como_secretario()
        # self.acessar_polo()
        # self.cadastrar_atividade_polo()

        # GERAÇÃO DE TURMAS E DIARIOS
        self.cadastrar_calendario_academico(params={'descricao': 'Calendário 1'})
        self.gerar_turmas_diarios()
        self.cadastrar_professor_nao_servidor()
        self.transferir_posse_etapa()
        self.configurar_diario()
        self.acessar_como_professor()
        self.visualizar_locais_horario_aulas_professor()

        # MATRÍCULA INSTITUCIONAL
        self.acessar_como_secretario()
        self.acessar_painel_controle()
        self.efetuar_matricula_institucional()
        self.cancelar_matricula()
        self.efetuar_matricula_institucional()
        self.efetuar_matricula_turma()
        self.emitir_relatorio_alunos()
        self.emitir_relatorio_professores()
        self.emitir_relatorio_diarios()
        self.emitir_relatorio_ead()
        self.imprimir_comprovante_matricula()
        self.acessar_como_aluno()
        self.visualizar_dados_pessoais_e_academicos()
        self.atualizar_endereco()
        self.definir_email_institucional()
        self.visualizar_locais_horario_aulas_aluno()

        # LANÇAMENTO DAS NOTAS
        self.acessar_como_professor()
        self.lancar_aulas_faltas_professor()
        self.acessar_como_aluno()
        self.acompanhar_aulas()
        self.acessar_como_professor()
        self.cadastrar_material_didatico()
        self.vincular_material_didatico()
        self.acessar_como_aluno()
        self.visualizar_materiais_didaticos()
        self.acessar_como_professor()
        self.lancar_notas_professor(50)
        self.lancar_notas_professor(80, 5)
        self.lancar_notas_professor(None, 5)
        self.lancar_notas_professor(None)
        self.lancar_notas_professor(20)
        self.lancar_notas_professor(None)
        self.lancar_notas_professor(80)
        self.imprimir_diario()
        self.acessar_como_aluno()
        self.visualizar_boletim_individual()

        # ENTREGA E RELANÇAMENTO DE ETAPA
        self.acessar_como_professor()
        self.entregar_etapa()
        self.solicitar_relancamento_etapa()
        self.acessar_como_secretario()
        self.indeferir_solicitacao_relancamento_etapa()
        self.acessar_como_professor()
        self.solicitar_relancamento_etapa()
        self.acessar_como_secretario()
        self.alterar_aulas_faltas_notas()
        self.deferir_solicitacao_relancamento_etapa()
        self.emitir_relatorio_faltas(codigo_turma=self.retornar(Turma).codigo)
        self.emitir_relatorio_faltas(codigo_turma=self.retornar(Turma).codigo, contendo=self.retornar(Aluno).pessoa_fisica.nome)

        # ACESSANDO PAINEL DE CONTROLE
        self.acessar_painel_controle(conteudo='0981')
        self.relatorio_periodos_abertos(ano='2013', contem=True, contendo=self.retornar(Aluno).pessoa_fisica.nome)

        # FECHAMENTO DO PERÍODO COM PENDÊNCIA E SEM FORÇAMENTO
        self.transferir_posse_etapa_registro_escolar()
        self.lancar_notas_secretario('')
        self.fechar_periodo(False, SituacaoMatricula.MATRICULADO, SituacaoMatriculaPeriodo.MATRICULADO, MatriculaDiario.SITUACAO_CURSANDO)

        # FECHAMENTO DO PERÍODO COM PENDÊNCIA E COM FORÇAMENTO
        self.acessar_como_administrador()
        self.abrir_periodo()
        self.acessar_como_secretario()
        self.lancar_notas_secretario('')
        self.fechar_periodo(True, SituacaoMatricula.NAO_CONCLUIDO, SituacaoMatriculaPeriodo.REPROVADO, MatriculaDiario.SITUACAO_REPROVADO)

        # FECHAMENTO DO PERÍODO SEM PENDÊNCIA E SEM FORÇAMENTO
        self.acessar_como_administrador()
        self.abrir_periodo()
        self.acessar_como_secretario()
        self.lancar_notas_secretario(80)
        self.fechar_periodo(False, SituacaoMatricula.CONCLUIDO, SituacaoMatriculaPeriodo.APROVADO, MatriculaDiario.SITUACAO_APROVADO)
        self.relatorio_periodos_abertos(ano='2013', contem=False, contendo=self.retornar(Aluno).pessoa_fisica.nome)

        # CONFIGURAÇÃO DO LIVRO DE REGISTRO DE DIPLOMA
        self.acessar_como_administrador()
        self.configurar_livro()
        self.cadastrar_processo()

        self.fechar_periodo(False, SituacaoMatricula.CONCLUIDO, SituacaoMatriculaPeriodo.APROVADO, MatriculaDiario.SITUACAO_APROVADO)

        # EMISSÃO DO CERTIFICADO
        self.emitir_diploma_lote()
        self.acessar_como_secretario()
        self.imprimir_registro_emissao_diploma()
        self.visualizar_historico(True)

        # ENVIO DE MENSAGEM
        self.acessar_como_secretario()
        self.enviar_mensagem()
        self.acessar_como_aluno()
        self.caixa_entrada_aluno()

        # ESTATÍSTICA
        self.acessar_como_administrador()
        self.relatorio_estatisticas()

        self.acessar_como_aluno()
        self.visualizar_dados_pessoais_e_academicos(ja_selecionou_email=True)

    def acessar_painel_controle(self, conteudo=None):
        url = '/edu/painel_controle/'
        response = self.client.get(url)
        self.assertContains(response, 'Painel de Controle')

        if conteudo:
            self.assertContains(response, conteudo)


class PosGraduacaoTestCase(EduTestCase):
    def setUp(self):
        super().setUp()
        self.initial_data['TipoComponente'] = self.retornar(TipoComponente, chaves={'descricao': 'POS'})
        self.initial_data['NivelEnsino'] = NivelEnsino.objects.get(pk=NivelEnsino.POS_GRADUACAO)
        self.initial_data['TipoAtividadeComplementar'] = self.retornar(TipoAtividadeComplementar, chaves={'descricao': 'Palestra'})
        self.initial_data['LinhaPesquisa'] = self.retornar(LinhaPesquisa, chaves={'descricao': 'Educação'})
        self.initial_data['Matriz'] = self.retornar(Matriz, chaves={'descricao': 'Mestrado em Agricultor Familiar'})
        self.initial_data['Professor'] = self.retornar(Professor)

    def cadastrar_configuracao_atividade_complementar(self, descricao='Padrão'):
        return self.cadastrar(ConfiguracaoAtividadeComplementar, dict(descricao=descricao))

    def efetuar_tansferencia_turma(self):
        turma_origem, turma_destino = self.retornar(Turma, 2)
        matricula_periodo = MatriculaPeriodo.objects.filter(turma=turma_origem)[0]
        # 1º passo do wizard: carregar a página.
        url = f'/edu/transferir_turma/{turma_origem.pk}/{matricula_periodo.pk}/'
        self.client.get(url)

        # 2º passo do wizard: preencher a turma destino.
        data = dict(turma_destino=turma_destino.pk)
        self.client.post(url, data)

        data.update(dict(confirmacao='on'))
        self.client.post(url, data)

        matricula_diario = MatriculaDiario.objects.filter(diario__turma=turma_origem)[0]
        self.assertEqual(matricula_diario.situacao, MatriculaDiario.SITUACAO_TRANSFERIDO)

    def excluir_turma(self):
        turma = self.retornar(Turma)
        turma.delete()

    def efetuar_matricula_turma(self):
        turma = self.retornar(Turma)
        numero_matriculas_diario_antes = MatriculaDiario.objects.count()
        url = f'/edu/turma/{turma.pk}/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Alunos', status_code=200)
        url = f'/edu/adicionar_aluno_turma/{turma.pk}/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Aluno à Turma', status_code=200)
        data = dict(matriculas_periodo=[turma.get_alunos_apto_matricula()[0].pk])
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        numero_matriculas_diario_depois = MatriculaDiario.objects.count()
        self.assertEqual(numero_matriculas_diario_depois, numero_matriculas_diario_antes + turma.diario_set.count())

    def efetuar_matricula_em_diario(self):
        aluno = self.retornar(Aluno)
        url = f'/edu/listar_diarios_matricula_aluno/{aluno.get_ultima_matricula_periodo().pk}/'
        response = self.client.get(url)
        self.assertContains(response, 'Matricular em Diário', status_code=200)
        diretoria = self.retornar(Diretoria)
        data = dict(diretoria=diretoria.pk)
        diario = self.retornar(Diario)
        url = f'/edu/matricular_aluno_diario/{aluno.get_ultima_matricula_periodo().pk}/{diario.pk}/'
        response = self.client.get(url, data)
        self.assert_no_validation_errors(response)

    def visualizar_configuracao_atividade_complementar(self):
        configuracao_atividade_complementar = self.retornar(ConfiguracaoAtividadeComplementar)
        url = f'/edu/configuracaoatividadecomplementar/{configuracao_atividade_complementar.pk}/'
        response = self.client.get(url)
        self.assertContains(response, 'Configuração da AACC', status_code=200)

    def cadastrar_item_configuracao_atividade_complementar(self):
        antes = ItemConfiguracaoAtividadeComplementar.objects.count()
        configuracao_atividade_complementar = self.retornar(ConfiguracaoAtividadeComplementar)
        url = f'/edu/adicionar_item_configuracao_aacc/{configuracao_atividade_complementar.pk}/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Atividade Acadêmica', status_code=200)
        data = dict(tipo=self.retornar(TipoAtividadeComplementar).pk, pontuacao_max_periodo=20, pontuacao_max_curso=40, fator_conversao=1.00)
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        depois = ItemConfiguracaoAtividadeComplementar.objects.count()
        self.assertContains(response, 'Atividade acadêmica cadastrada com sucesso.', status_code=200)
        self.assertEqual(depois, antes + 1)

    def excluir_item_configuracao_atividade_complementar(self):
        antes = ItemConfiguracaoAtividadeComplementar.objects.count()
        configuracao_atividade_complementar = self.retornar(ConfiguracaoAtividadeComplementar)
        item = ItemConfiguracaoAtividadeComplementar.objects.filter(configuracao=configuracao_atividade_complementar)[0]
        url = f'/comum/excluir/edu/itemconfiguracaoatividadecomplementar/{item.pk}/'
        data = dict(senha='123')
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Registro(s) excluído(s) com sucesso.', status_code=200)
        depois = ItemConfiguracaoAtividadeComplementar.objects.count()
        self.assertEqual(depois, antes - 1)

    def vincular_matriz_configuracao_atividade_complementar(self):
        matriz = self.retornar(Aluno).matriz
        configuracao_atividade_complementar = self.retornar(ConfiguracaoAtividadeComplementar)
        antes = configuracao_atividade_complementar.matriz_set.count()
        url = f'/edu/vincular_configuracao_atividade_complementar/{configuracao_atividade_complementar.pk}/'
        response = self.client.get(url)
        self.assertContains(response, 'Vincular Matriz', status_code=200)
        data = dict(matrizes=[matriz.pk])
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Matrizes vinculadas com sucesso.', status_code=200)

        url2 = f'/edu/configuracaoatividadecomplementar/{configuracao_atividade_complementar.pk}/?desvincular_matriz={self.retornar(Matriz).pk}'
        response = self.client.get(url2, follow=True)
        self.assertContains(response, 'Matriz desvinculada com sucesso.')

        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Matrizes vinculadas com sucesso.', status_code=200)
        depois = configuracao_atividade_complementar.matriz_set.count()
        self.assertEqual(depois, antes + 1)

    def cadastrar_atividade_complementar(self, curricular=True):
        antes = AtividadeComplementar.objects.count()
        aluno = self.retornar(Aluno)
        matricula_periodo = aluno.matriculaperiodo_set.all()[0]
        ano_letivo = matricula_periodo.ano_letivo
        periodo_letivo = matricula_periodo.periodo_letivo
        url = f'{aluno.get_absolute_url()}?tab=acc'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Atividade Complementar', status_code=200)

        url = f'/edu/cadastrar_atividade_complementar/{aluno.pk}/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Atividade Complementar', status_code=200)

        if curricular:
            tipo = TipoAtividadeComplementar.objects.filter(itemconfiguracaoatividadecomplementar__isnull=False)[0]
            data = dict(
                vinculacao=AtividadeComplementarForm.VINCULADO_CURSO,
                aluno=aluno.pk,
                descricao='Participação no congresso',
                tipo=tipo.pk,
                ano_letivo=ano_letivo.pk,
                periodo_letivo=periodo_letivo,
                data_atividade='01/07/2014',
                carga_horaria=8,
                informacoes_complementares='Atuou como auxiliar técnico',
                documento='',
                deferida='on',
            )
        else:
            tipo = TipoAtividadeComplementar.objects.filter(itemconfiguracaoatividadecomplementar__isnull=True)[0]
            data = dict(
                vinculacao=AtividadeComplementarForm.NAO_VINCULADO_CURSO,
                aluno=aluno.pk,
                descricao='Palestra em congresso',
                tipo=tipo.pk,
                ano_letivo=ano_letivo.pk,
                periodo_letivo=periodo_letivo,
                data_atividade='05/08/2014',
                carga_horaria=12,
                informacoes_complementares='Atuou como palestrante',
                documento='',
                deferida='on',
            )

        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, '', status_code=200)
        depois = AtividadeComplementar.objects.count()
        self.assertEqual(depois, antes + 1)

    def excluir_atividade_complementar(self):
        antes = AtividadeComplementar.objects.count()
        atividade_complementar = self.retornar(AtividadeComplementar)
        url = f'/comum/excluir/edu/atividadecomplementar/{atividade_complementar.pk}/'
        data = dict(senha='123')
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Registro(s) excluído(s) com sucesso.', status_code=200)
        depois = AtividadeComplementar.objects.count()
        self.assertEqual(depois, antes - 1)

    def visualizar_atividade_complementar(self, curricular=True):
        atividade_complementar = self.retornar(AtividadeComplementar)
        url = f'/edu/visualizar_atividade_complementar/{atividade_complementar.pk}/'
        response = self.client.get(url)
        if not curricular:
            self.assertContains(response, 'Não', status_code=200)
        else:
            self.assertContains(response, 'Sim', status_code=200)

    def cadastrar_projeto_final(self):

        # cadastrando o projeto final
        aluno = self.retornar(Aluno)
        url = f'/edu/adicionar_projeto_final/{aluno.id}/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar', status_code=200)

        projetos_finais_antes = ProjetoFinal.objects.all().count()
        professor = self.retornar(Professor)

        # carregando dados para cadastro de um projeto final
        data = dict(
            aluno=aluno.pk,
            ano_letivo=self.ano_2014.pk,
            periodo_letivo='1',
            titulo='Titulo do projeto final.',
            resumo='Resumo do projeto final.',
            tipo='Relatório de Projeto',
            orientador=professor.vinculo.pessoa.pk,
            data_defesa='01/08/2014',
            local_defesa=self.retornar(Sala).pk,
            presidente=professor.pk,
        )
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'TCC / Relatório adicionado com sucesso')
        projetos_finais_depois = ProjetoFinal.objects.all().count()
        self.assertEqual(projetos_finais_depois, projetos_finais_antes + 1)

        # Verificando link de lançar resultado
        projeto_final = self.retornar(ProjetoFinal)
        url = f'/edu/lancar_resultado_projeto_final/{projeto_final.pk}/'
        response = self.client.get(url)
        self.assertContains(response, 'Lançar Resultado', status_code=200)

        # realizando o lançamento do resultado
        documento = open('edu/fixtures/test_projeto_final.pdf', 'r+b')
        data = dict(resultado_data='01/08/2014', nota='85', situacao=ProjetoFinal.SITUACAO_APROVADO, tipo_documento='1', documento_url='http://www.google.com', ata=documento)
        response = self.client.post(url, data, follow=True)
        documento.close()
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Resultado registrado com sucesso.')

    def excluir_projeto_final(self):
        url = f'/comum/excluir/edu/projetofinal/{1}/'
        data = dict(senha='123')
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Registro(s) excluído(s) com sucesso.', status_code=200)

        # Verificando se a nota no diario foi setada para Nulo
        matricula_diario = self.retornar(MatriculaDiario)
        self.assertEqual(matricula_diario.nota_1, None)

        # apagando o diário referente ao projeto final
        matricula_diario.diario.delete()

    def importar_edital(self):
        # Configurando arquivos de editais
        WebService.objects.get_or_create(
            descricao='WebService1', url_editais='file://edu/fixtures/editais.xml', url_edital='file://edu/fixtures/edital10.xml', url_candidato='file://edu/fixtures/candidato.xml'
        )

        # Importando edital
        count_edital = Edital.objects.count()
        webservice = self.retornar(WebService)
        count_lista = Lista.objects.count()
        count_candidato = Candidato.objects.count()
        count_candidato_vaga = CandidatoVaga.objects.count()
        url = '/processo_seletivo/importar_edital/?test=1'
        data = dict(ano=self.ano_2013.pk, semestre=1, webservice=webservice.pk)
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        data.update(edital=10)
        response = self.client.post(url, data, follow=True)

        self.assert_no_validation_errors(response)
        self.assertEqual(Edital.objects.count(), count_edital + 1)
        self.assertEqual(Lista.objects.count(), count_lista + 2)
        self.assertEqual(Candidato.objects.count(), count_candidato + 1)
        self.assertEqual(CandidatoVaga.objects.count(), count_candidato_vaga + 1)

        # Acessando os editais
        url = '/admin/processo_seletivo/edital/'
        response = self.client.get(url)
        self.assertContains(response, 'Mostrando 1')

        # Acessando o edital
        edital = self.retornar(Edital)

        url = f'/processo_seletivo/edital/{edital.pk}/'
        response = self.client.get(url)
        self.assertContains(response, 'Edital 002/2014')

        # Acessando o candidato
        candidato = self.retornar(Candidato)
        url = f'/processo_seletivo/edital/{edital.pk}/?tab=candidatos'
        response = self.client.get(url)
        self.assertContains(response, candidato.nome)

    def definir_formas_ingresso(self):
        edital = Edital.objects.latest('id')
        for lista in edital.lista_set.all():
            forma_ingresso = self.retornar(FormaIngresso)
            url = f'/processo_seletivo/definir_forma_ingresso/{lista.id}/'
            data = dict(forma_ingresso=forma_ingresso.pk)
            response = self.client.post(url, data, follow=True)
            self.assertContains(response, 'Forma de ingresso definida com sucesso', status_code=200)

    def realizar_convocacao(self):
        oferta_vaga_curso = self.retornar(OfertaVagaCurso)
        count1 = CandidatoVaga.objects.filter(convocacao__isnull=True).count()
        url = '/processo_seletivo/edital/{}/?nova_chamada={}'.format(Edital.objects.latest('id').id, oferta_vaga_curso.pk)
        response = self.client.post(url, {}, follow=True)
        self.assert_no_validation_errors(response)
        count2 = CandidatoVaga.objects.filter(convocacao__isnull=True).count()
        self.assertNotEqual(count1, count2)

    def identificar_canditado(self):
        # Primeiro Passo do Wizard
        url = '/edu/identificar_candidato/'
        data = dict(ano=self.ano_2013.pk, semestre=1)
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)

        # Segundo Passo do Wizard
        data.update(edital=10)
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)

        # Terceiro Passo do Wizard
        data.update(cpf='047.704.024-14')
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)

        # Quarto Passo do Wizard
        data.update(candidato_vaga=CandidatoVaga.objects.filter(candidato__cpf='047.704.024-14')[0])
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)

    def vincular_prerequisito(self, inserir, receptor, pre_requisito):
        for descricao in ('PÓS-GRADUAÇAO SERIADO', 'PÓS-GRADUAÇAO CRÉDITO'):
            componente_curricular_receptor = ComponenteCurricular.objects.get(componente__descricao=receptor, matriz__estrutura__descricao=descricao)
            componente_curricular_prerequisito = ComponenteCurricular.objects.get(componente__descricao=pre_requisito, matriz__estrutura__descricao=descricao)

            if inserir:
                componente_curricular_receptor.pre_requisitos.add(componente_curricular_prerequisito)
            else:
                componente_curricular_receptor.pre_requisitos.remove(componente_curricular_prerequisito)

    def vincular_correquisito(self, inserir, receptor, correquisito):
        for descricao in ('PÓS-GRADUAÇAO SERIADO', 'PÓS-GRADUAÇAO CRÉDITO'):
            componente_curricular_receptor = ComponenteCurricular.objects.get(componente__descricao=receptor, matriz__estrutura__descricao=descricao)
            componente_curricular_correquisito = ComponenteCurricular.objects.get(componente__descricao=correquisito, matriz__estrutura__descricao=descricao)

            if inserir:
                componente_curricular_receptor.co_requisitos.add(componente_curricular_correquisito)
            else:
                componente_curricular_receptor.co_requisitos.remove(componente_curricular_correquisito)

    def cadastrar_justificativa_dispensa(self):
        count = JustificativaDispensaENADE.objects.count()
        url = '/admin/edu/justificativadispensaenade/add/'
        data = dict(descricao='Estudante dispensado conforme Art. 6º, § 2 da Portaria Normativa Nº8 de 14 março de 2014.')
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertEqual(JustificativaDispensaENADE.objects.count(), count + 1)

    def cadastrar_convocacao_enade(self, ano_letivo=None):
        aluno = self.retornar(Aluno)
        matricula_periodo = aluno.matriculaperiodo_set.all()[0]
        if not ano_letivo:
            ano_letivo = matricula_periodo.ano_letivo
        curso = aluno.curso_campus
        curso.exige_enade = True
        curso.save()

        count_convocacoesenade = ConvocacaoENADE.objects.count()
        url = '/admin/edu/convocacaoenade/add/'
        data = dict(
            ano_letivo=ano_letivo.pk,
            cursos=[curso.pk],
            data_prova='',
            percentual_minimo_ingressantes=0,
            percentual_maximo_ingressantes=49,
            percentual_minimo_concluintes=50,
            percentual_maximo_concluintes=100,
        )
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertEqual(ConvocacaoENADE.objects.count(), count_convocacoesenade + 1)

    def processar_convocados_enade(self):
        convocacao_enade = self.retornar(ConvocacaoENADE)
        url = f'/edu/atualizar_lista_convocados_enade/{convocacao_enade.pk}/?curso_campus='
        response = self.client.get(url, follow=True)
        self.assert_no_validation_errors(response)

    def editar_convocacao_enade(self):
        convocacao_enade = self.retornar(ConvocacaoENADE)
        url = f'/admin/edu/convocacaoenade/{convocacao_enade.pk}/change/'
        data = dict(
            ano_letivo=convocacao_enade.ano_letivo.pk,
            cursos=convocacao_enade.cursos.all().values_list('pk', flat=True),
            data_prova='01/06/2015',
            percentual_minimo_ingressantes=0,
            percentual_maximo_ingressantes=50,
            percentual_minimo_concluintes=51,
            percentual_maximo_concluintes=100,
        )
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)

    def lancar_situacao_enade_aluno(self):
        convocacao_enade = self.retornar(ConvocacaoENADE)
        registro = convocacao_enade.registroconvocacaoenade_set.first()
        url = f'/edu/lancar_situacao_enade/{registro.pk}/'
        data = dict(situacao=RegistroConvocacaoENADE.SITUACAO_PRESENTE)
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)


class EduPosTestCase(PosGraduacaoTestCase):
    def setUp(self):
        super().setUp()
        self.initial_data['MatrizCurso'] = self.retornar(
            MatrizCurso, chaves={'matriz__descricao': 'Mestrado em Agricultor Familiar', 'curso_campus__descricao': 'Mestrado em Agricultor Familiar'}
        )
        self.initial_data['CursoCampus'] = self.retornar(CursoCampus, chaves={'descricao': 'Mestrado em Agricultor Familiar'})
        self.initial_data['FormaIngresso'] = self.retornar(FormaIngresso, chaves={'descricao': 'Processo Seletivo'})

    def evasao_em_lote(self):
        aluno = self.retornar(Aluno)
        situacao_inicial = aluno.situacao.id
        # acessando a evasao em lote
        ultima_matricula_periodo = aluno.get_ultima_matricula_periodo()
        url = '/edu/evasao_em_lote/?ano_letivo={:d}&periodo_letivo={:d}&uo=&curso_campus=&curso_campus='.format(
            ultima_matricula_periodo.ano_letivo.pk, ultima_matricula_periodo.periodo_letivo
        )
        response = self.client.get(url, follow=True)
        # evadindo o aluno
        self.assertContains(response, 'Em Aberto', status_code=200)

        url = f'/edu/evadir_aluno/{aluno.id}/'
        data = dict(alunos_selecionados=[aluno.id])
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Aluno evadido com sucesso.')
        aluno = self.recarregar(aluno)
        self.assertEqual(aluno.situacao.id, SituacaoMatricula.EVASAO)

        # desfazendo a evasao
        url = f'/edu/aluno/{aluno.matricula}/?tab=procedimentos'
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Desfazer Procedimento', status_code=200)
        procedimento = ProcedimentoMatricula.objects.get(matricula_periodo__in=aluno.matriculaperiodo_set.all())
        url = f'/edu/aluno/{aluno.matricula}/?tab=procedimentos&procedimento_id={procedimento.pk:d}'
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Procedimento desfeito com sucesso!', status_code=200)
        aluno = self.recarregar(aluno)
        self.assertEqual(aluno.situacao.id, situacao_inicial)

    def test_fluxo(self):
        # VINCULAÇÃO DOS USUÁRIOS
        self.vincular_usuario_a_diretoria('Secretário Acadêmico')
        self.vincular_usuario_a_diretoria('Coordenador de Registros Acadêmicos')

        # GERAÇÃO DE TURMAS E DIARIOS
        self.acessar_como_secretario()
        self.cadastrar_calendario_academico(tipo=CalendarioAcademico.TIPO_SEMESTRAL)
        self.gerar_turmas_diarios()
        self.cadastrar_professor_nao_servidor()
        self.transferir_posse_etapa()
        self.configurar_diario()

        self.acessar_como_professor()
        self.visualizar_locais_horario_aulas_professor()

        # IMPORTAÇÃO DO EDITAL
        self.acessar_como_administrador()
        self.importar_edital()
        self.definir_formas_ingresso()

        # MATRÍCULA INSTITUCIONAL POR PROCESSO SELETIVO
        self.acessar_como_secretario()
        self.identificar_canditado()
        self.efetuar_matricula_institucional()
        self.cancelar_matricula()
        self.identificar_canditado()
        self.efetuar_matricula_institucional()
        self.efetuar_matricula_turma()
        self.emitir_relatorio_alunos()
        self.imprimir_comprovante_matricula()

        self.acessar_como_aluno()
        self.visualizar_dados_pessoais_e_academicos()
        self.atualizar_endereco()
        self.definir_email_institucional()
        self.visualizar_locais_horario_aulas_aluno()

        # CONVOCAÇÃO DO ENADE
        self.acessar_como_regulador_avaliador()
        self.cadastrar_justificativa_dispensa()
        self.cadastrar_convocacao_enade()
        self.editar_convocacao_enade()
        self.processar_convocados_enade()

        self.acessar_como_operador_enade()
        self.lancar_situacao_enade_aluno()

        # LANÇAMENTO DAS NOTAS
        self.acessar_como_professor()
        self.lancar_aulas_faltas_professor()
        self.imprimir_diario()

        self.acessar_como_aluno()
        self.acompanhar_aulas()

        self.acessar_como_professor()
        self.cadastrar_material_didatico()
        self.vincular_material_didatico()

        self.acessar_como_aluno()
        self.visualizar_materiais_didaticos()

        self.acessar_como_aluno()
        self.visualizar_boletim_individual()

        # ENTREGA DE ETAPA
        self.acessar_como_professor()
        self.lancar_notas_professor()
        self.alterar_configuracao_avaliacao()
        self.entregar_etapa()

        self.acessar_como_secretario()
        self.fechar_periodo(False, SituacaoMatricula.MATRICULADO, SituacaoMatriculaPeriodo.APROVADO, MatriculaDiario.SITUACAO_APROVADO)

        # CADASTRO DE CONFIGURAÇÃO DE ATIVIDADES COMPLEMENTARES

        self.acessar_como_administrador()
        self.cadastrar_configuracao_atividade_complementar()
        self.visualizar_configuracao_atividade_complementar()
        self.cadastrar_item_configuracao_atividade_complementar()
        self.excluir_item_configuracao_atividade_complementar()
        self.cadastrar_item_configuracao_atividade_complementar()
        self.vincular_matriz_configuracao_atividade_complementar()

        # CADASTRO DE ATIVIDADES COMPLEMENTARES
        self.acessar_como_secretario()
        self.cadastrar_atividade_complementar()
        self.cadastrar_atividade_complementar(False)
        self.visualizar_atividade_complementar(False)
        self.excluir_atividade_complementar()
        self.visualizar_atividade_complementar()

        self.acessar_como_aluno()
        self.visualizar_atividade_complementar()

        # SEGUNDO PERÍODO DO CURSO (GERAÇÃO DE TURMAS E DIÁRIOS)
        self.acessar_como_secretario()
        self.cadastrar_calendario_academico(self.ano_2013, 2, CalendarioAcademico.TIPO_SEMESTRAL)
        self.gerar_turmas_diarios(self.ano_2013, 2, 2, qtd_turmas=1)
        self.configurar_diario()

        self.gerar_turmas_diarios(self.ano_2013, 2, 2, qtd_turmas=2)
        self.configurar_diario()

        self.acessar_como_professor()
        self.visualizar_locais_horario_aulas_professor()

        # TESTANDO A EVASÃO EM LOTE
        self.acessar_como_secretario()
        self.evasao_em_lote()

        # MATRÍCULA DA TURMA DO SEGUNDO PERÍODO
        self.acessar_como_secretario()

        self.efetuar_matricula_turma()
        self.efetuar_tansferencia_turma()
        self.excluir_turma()

        self.emitir_relatorio_alunos()
        self.imprimir_comprovante_matricula()

        # LANÇAMENTO DAS NOTAS
        self.acessar_como_professor()
        self.lancar_aulas_faltas_professor()
        self.lancar_notas_professor()

        self.acessar_como_aluno()
        self.acompanhar_aulas()

        # ENTREGA DA ETAPA
        self.acessar_como_professor()
        self.entregar_etapa()

        self.acessar_como_secretario()
        self.fechar_periodo(False, SituacaoMatricula.MATRICULADO, SituacaoMatriculaPeriodo.APROVADO, MatriculaDiario.SITUACAO_APROVADO)

        # CONVOCAÇÃO DO ENADE
        self.acessar_como_regulador_avaliador()
        self.cadastrar_convocacao_enade(self.ano_2014)
        self.editar_convocacao_enade()
        self.processar_convocados_enade()

        self.acessar_como_operador_enade()
        self.lancar_situacao_enade_aluno()

        # TERCEIRO PERÍODO DO CURSO (GERAÇÃO DE TURMAS E DIÁRIO COM  DISCIPLINA DE TCC)
        self.acessar_como_secretario()
        self.cadastrar_calendario_academico(self.ano_2014, 1, CalendarioAcademico.TIPO_SEMESTRAL)
        self.gerar_turmas_diarios(self.ano_2014, 1, 3)
        self.configurar_diario()

        self.acessar_como_professor()
        self.visualizar_locais_horario_aulas_professor()

        # MATRÍCULA DA TURMA DO TERCEIRO PERÍODO
        self.acessar_como_secretario()
        self.efetuar_matricula_turma()

        # CADASTRO DOS ENCONTROS COM O ALUNO
        self.acessar_como_professor()
        self.lancar_aulas_faltas_professor(self.ano_2014)
        self.lancar_notas_professor()

        # LANÇAMENTO DA NOTA DO PROJETO FINAL
        self.acessar_como_secretario()
        self.cadastrar_projeto_final()
        # self.excluir_projeto_final()

        # ENTREGA DA ETAPA
        self.acessar_como_professor()
        self.entregar_etapa()

        # FECHANDO O TERCEIRO E ÚLTIMO PERÍODO
        self.acessar_como_secretario()
        # lançar dispensa ENADE

        self.fechar_periodo(False, SituacaoMatricula.CONCLUIDO, SituacaoMatriculaPeriodo.APROVADO, MatriculaDiario.SITUACAO_APROVADO)

        # PROCEDIMENTOS DE MATRÍCULA
        self.cadastrar_processo()
        self.acessar_como_administrador()
        self.abrir_periodo()
        self.acessar_como_secretario()
        self.procedimento_matricula(SituacaoMatricula.CANCELAMENTO_COMPULSORIO)
        self.desfazer_ultimo_procedimento_matricula()
        self.procedimento_matricula(SituacaoMatricula.CANCELAMENTO_POR_DESLIGAMENTO)
        self.desfazer_ultimo_procedimento_matricula()
        self.procedimento_matricula(SituacaoMatricula.CANCELAMENTO_POR_DUPLICIDADE)
        self.desfazer_ultimo_procedimento_matricula()
        self.procedimento_matricula(SituacaoMatricula.CANCELADO)
        self.desfazer_ultimo_procedimento_matricula()
        self.procedimento_matricula(SituacaoMatricula.EVASAO)
        self.desfazer_ultimo_procedimento_matricula()
        self.procedimento_matricula(SituacaoMatricula.JUBILADO)
        self.desfazer_ultimo_procedimento_matricula()
        self.procedimento_matricula(SituacaoMatricula.INTERCAMBIO)
        self.desfazer_ultimo_procedimento_matricula()
        self.procedimento_matricula(SituacaoMatricula.TRANCADO)
        self.desfazer_ultimo_procedimento_matricula()

        self.procedimento_matricula(SituacaoMatricula.CANCELADO)
        self.pc_reintegracao(self.ano_2014, '2')
        self.desfazer_ultimo_procedimento_matricula()
        self.desfazer_ultimo_procedimento_matricula()

        # FECHANDO O TERCEIRO E ÚLTIMO PERÍODO
        self.acessar_como_secretario()
        self.fechar_periodo(False, SituacaoMatricula.CONCLUIDO, SituacaoMatriculaPeriodo.APROVADO, MatriculaDiario.SITUACAO_APROVADO)

        # CONFIGURAÇÃO DO LIVRO DE REGISTRO DE DIPLOMA
        self.acessar_como_administrador()
        self.configurar_livro()
        self.cadastrar_processo()

        # EMISSÃO DO DIPLOMA
        self.acessar_como_secretario()
        self.emitir_diploma()
        self.imprimir_registro_emissao_diploma()
        self.visualizar_historico(True)

        self.acessar_como_aluno()
        self.visualizar_dados_pessoais_e_academicos(ja_selecionou_email=True, com_atividades_complementares=True)


class QEduTestCase(PosGraduacaoTestCase):
    def setUp(self):
        super().setUp()
        self.initial_data['FormaIngresso'] = self.retornar(FormaIngresso, chaves={'descricao': 'Integração Q-Acadêmico'})
        self.initial_data['NaturezaParticipacao'] = self.retornar(NaturezaParticipacao, chaves={'descricao': 'Presencial'})
        self.initial_data['EstruturaCurso'] = self.retornar(EstruturaCurso, chaves={'descricao': 'PÓS-GRADUAÇAO (SERIADO)'})

    def importar_dados(self):
        call_command('edu_importar_dados', verbosity=0)
        self.assertEqual(self.retornar(CursoCampus, chaves={'descricao': 'Curso Importado'}).descricao, 'Curso Importado')
        self.assertEqual(self.retornar(Aluno, chaves={'matricula': '270636252864'}).matricula, '270636252864')

    def ativar_curso_importado(self):
        curso = self.retornar(CursoCampus)
        # acessando a página de cadastro de curso
        url = f'/admin/edu/cursocampus/{curso.pk}/change/'
        response = self.client.get(url)
        self.assertContains(response, f'Editar {curso}', status_code=200)
        natureza_participacao = self.retornar(NaturezaParticipacao)
        turno = self.retornar(Turno)
        modalidade = self.retornar(Modalidade)
        estrutura = self.retornar(EstruturaCurso)
        diretoria = self.retornar(Diretoria)
        area = self.retornar(AreaCurso)
        eixo = self.retornar(EixoTecnologico)
        area_capes = self.retornar(AreaCapes)
        data = dict(
            descricao='Curso Importado',
            descricao_historico='Curso Importado',
            ano_letivo=self.ano_2013.pk,
            periodo_letivo='1',
            data_inicio='17/06/2013',
            data_fim='',
            ativo='on',
            codigo='1234',
            natureza_participacao=natureza_participacao.pk,
            turno=turno.pk,
            modalidade=modalidade.pk,
            area=area.pk,
            eixo=eixo.pk,
            area_capes=area_capes.pk,
            estrutura=estrutura.pk,
            periodicidade=CursoCampus.PERIODICIDADE_SEMESTRAL,
            diretoria=diretoria.pk,
            emite_diploma=True,
            titulo_certificado_masculino='Certificado',
            titulo_certificado_feminino='Certificada',
        )
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        return self.retornar(CursoCampus)

    def integralizar_aluno(self):
        matriz = self.retornar(Matriz)
        # acessando a página de integralização dos alunos do Q-Acadêmico
        url = f'/edu/integralizar_alunos/{matriz.id}/'
        response = self.client.get(url)
        self.assertContains(response, 'Migração de Alunos Ativos do Q-Acadêmico', status_code=200)
        arquivo = open('edu/fixtures/test_integralizacao.xlsx', 'r+b')
        data = dict(ano_letivo=self.ano_2013.pk, periodo_letivo='2', arquivo=arquivo)
        response = self.client.post(url, data)
        arquivo.close()
        self.assert_no_validation_errors(response)
        self.assertEqual(self.retornar(Aluno).matriz, matriz)

    def atualizar_dados_aluno_integralizado(self):
        aluno = self.retornar(Aluno)
        cidade = Cidade.objects.get(codigo=2401403)
        convenio = self.retornar(Convenio)
        url = f'/admin/edu/aluno/{aluno.pk}/change/'
        response = self.client.get(url)
        self.assertContains(response, 'Editar ', status_code=200)
        count = Aluno.objects.all().count()

        data = dict(
            nome=aluno.pessoa_fisica.nome,
            nome_mae='Maria da Silva',
            cpf=aluno.pessoa_fisica.cpf,
            data_nascimento='27/08/1984',
            estado_civil='Solteiro',
            sexo=aluno.pessoa_fisica.sexo,
            nacionalidade='Brasileira',
            naturalidade=cidade.pk,
            turno=aluno.turno.pk,
            logradouro='Av. Pedro e Silva',
            numero='908',
            bairro='Centro',
            cidade=cidade.pk,
            cota_sistec=9,
            cota_mec=0,
            forma_ingresso=self.retornar(FormaIngresso).pk,
            raca=self.raca.pk,
            tipo_instituicao_origem=Aluno.TIPO_INSTITUICAO_ORIGEM_CHOICES[0][0],
            tipo_zona_residencial=Aluno.TIPO_ZONA_RESIDENCIAL_CHOICES[0][0],
            possui_convenio=True,
            convenio=convenio.pk,
        )
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(Aluno.objects.all().count(), count)

    def realizar_equivalencia_componente_qacademico(self):
        componente = self.retornar(Componente, chaves={'sigla': 'POS.0001'})
        equivalencia_componente_qacademico = self.retornar(EquivalenciaComponenteQAcademico)

        # acessando o histórico antes da equivalencia
        aluno = self.retornar(Aluno)
        url_historico = f'/edu/emitir_historico_parcial_pdf/{aluno.id}/?html=1'
        response = self.client.get(url_historico)
        self.assertContains(response, equivalencia_componente_qacademico.sigla, status_code=200)

        # acessando a página de equivalencia do componente importado do Q-Acadêmico
        url = f'/admin/edu/equivalenciacomponenteqacademico/{equivalencia_componente_qacademico.id}/change/'
        response = self.client.get(url, follow=True)
        self.assertContains(response, f'Editar {equivalencia_componente_qacademico.sigla}', status_code=200)
        data = dict(
            q_academico=equivalencia_componente_qacademico.q_academico,
            sigla=equivalencia_componente_qacademico.sigla,
            descricao=equivalencia_componente_qacademico.descricao,
            carga_horaria=equivalencia_componente_qacademico.carga_horaria,
            componente=componente.id,
        )
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)

        # acessando o histórico depois da equivalencia
        response = self.client.get(url_historico)
        self.assertNotContains(response, equivalencia_componente_qacademico.sigla, status_code=200)

    def test_fluxo(self):
        # VINCULAÇÃO DOS USUÁRIOS
        self.vincular_usuario_a_diretoria('Secretário Acadêmico')
        self.vincular_usuario_a_diretoria('Coordenador de Registros Acadêmicos')

        # IMPORTANDO E ATIVANDO O CURSO
        self.acessar_como_administrador()
        self.importar_dados()
        self.ativar_curso_importado()
        self.vincular_matriz_curso()
        self.cadastrar_convenio('PRONATEC')

        # ACESSANDO A PÁGINA DO ALUNO APÓS A IPORTAÇÃO
        self.acessar_como_aluno()
        self.visualizar_dados_pessoais_e_academicos(com_boletim=False, com_historico=False, com_atividades_complementares=True)

        # PRIMEIRO PERÍODO DO CURSO (INTEGRALIZAÇÃO DO ALUNO)
        self.acessar_como_administrador()
        self.integralizar_aluno()
        self.atualizar_dados_aluno_integralizado()
        self.realizar_equivalencia_componente_qacademico()

        # ACESSANDO A PÁGINA DO ALUNO APÓS A MIGRAÇÃO
        self.acessar_como_aluno()
        self.visualizar_dados_pessoais_e_academicos(ja_selecionou_email=True, com_boletim=False)

        # SEGUNDO PERÍODO DO CURSO (GERAÇÃO DE TURMAS E DIÁRIOS)
        self.acessar_como_secretario()
        self.cadastrar_calendario_academico(self.ano_2013, 2, CalendarioAcademico.TIPO_SEMESTRAL)
        self.gerar_turmas_diarios(self.ano_2013, 2, 2)
        self.cadastrar_professor_nao_servidor()
        self.transferir_posse_etapa()
        self.configurar_diario()

        self.acessar_como_professor()
        self.visualizar_locais_horario_aulas_professor()

        # MATRÍCULA DA TURMA DO SEGUNDO PERÍODO
        self.acessar_como_secretario()
        self.efetuar_matricula_turma()
        self.emitir_relatorio_alunos()
        self.imprimir_comprovante_matricula()

        self.efetuar_matricula_em_diario()

        self.acessar_como_aluno()
        self.visualizar_dados_pessoais_e_academicos()
        self.atualizar_endereco()
        self.definir_email_institucional()
        self.visualizar_locais_horario_aulas_aluno()

        # LANÇAMENTO DAS NOTAS
        self.acessar_como_professor()
        self.lancar_aulas_faltas_professor()
        self.lancar_notas_professor()

        self.acessar_como_aluno()
        self.acompanhar_aulas()

        self.acessar_como_professor()
        self.cadastrar_material_didatico()
        self.vincular_material_didatico()

        self.acessar_como_aluno()
        self.visualizar_materiais_didaticos()

        # JUSTIFICATIVA DE FALTAS

        self.acessar_como_secretario()
        self.abonar_falta()

        self.acessar_como_professor()
        self.imprimir_diario()

        self.acessar_como_aluno()
        self.visualizar_boletim_individual()

        # ENTREGA DA ETAPA
        self.acessar_como_professor()
        self.entregar_etapa()

        self.acessar_como_secretario()
        self.fechar_periodo(False, SituacaoMatricula.MATRICULADO, SituacaoMatriculaPeriodo.APROVADO, MatriculaDiario.SITUACAO_APROVADO)

        # TERCEIRO PERÍODO DO CURSO (GERAÇÃO DE TURMAS E DIÁRIO COM  DISCIPLINA DE TCC)
        self.acessar_como_secretario()
        self.cadastrar_calendario_academico(self.ano_2014, 1, CalendarioAcademico.TIPO_SEMESTRAL)
        self.gerar_turmas_diarios(self.ano_2014, 1, 3)
        self.configurar_diario()

        self.acessar_como_professor()
        self.visualizar_locais_horario_aulas_professor()

        # MATRÍCULA DA TURMA DO TERCEIRO PERÍODO
        self.acessar_como_secretario()
        self.efetuar_matricula_turma()

        # CADASTRO DOS ENCONTROS COM O ALUNO
        self.acessar_como_professor()
        self.lancar_aulas_faltas_professor(self.ano_2014)
        self.lancar_notas_professor()

        # LANÇAMENTO DA NOTA DO PROJETO FINAL
        self.acessar_como_secretario()
        self.cadastrar_projeto_final()
        # self.excluir_projeto_final()

        # ENTREGA DA ETAPA
        self.acessar_como_professor()
        self.entregar_etapa()

        # FECHANDO O TERCEIRO E ÚLTIMO PERÍODO
        self.acessar_como_secretario()
        self.fechar_periodo(False, SituacaoMatricula.CONCLUIDO, SituacaoMatriculaPeriodo.APROVADO, MatriculaDiario.SITUACAO_APROVADO)

        # CONFIGURAÇÃO DO LIVRO DE REGISTRO DE DIPLOMA
        self.acessar_como_administrador()
        self.configurar_livro()
        self.cadastrar_processo()

        # EMISSÃO DO DIPLOMA
        self.acessar_como_secretario()
        self.emitir_diploma()
        self.imprimir_registro_emissao_diploma()
        self.visualizar_historico(True)

        self.acessar_como_aluno()
        self.visualizar_dados_pessoais_e_academicos(ja_selecionou_email=True, com_atividades_complementares=True)


class MatriculaOnline(PosGraduacaoTestCase):
    def setUp(self):
        super().setUp()
        self.initial_data['FormaIngresso'] = self.retornar(FormaIngresso, chaves={'descricao': 'Processo Seletivo'})
        self.initial_data['Matriz'] = self.retornar(Matriz, chaves={'descricao': 'Mestrado'})

    def lancar_aulas_faltas_professor(self, ano=None, componente='A1'):
        if not ano:
            ano = self.ano_2013

        matricula_diario = MatriculaDiario.objects.get(diario__componente_curricular__componente__descricao=componente)
        professor_diario = ProfessorDiario.objects.get(diario__componente_curricular__componente__descricao=componente)

        # verificando a existência do link de acesso à página de visualização de etapa
        url = f'/edu/meu_diario/{matricula_diario.diario.pk}/1/'
        response = self.client.get(url)
        self.assertContains(response, url, status_code=200)
        # acessando a página de visualização da etapa 1, na aba "Aulas e Conteúdo"
        self.client.get(url)
        # verificando a existência do link de acesso à página de cadastro de aula
        url = f'/edu/adicionar_aula_diario/{matricula_diario.diario.pk}/1/'
        # self.assertContains(response, url)
        # acessando a página de cadastro de aula
        self.client.get(url)
        # registrando uma aula para atingir 80% da carga horária necessária (8 de 10)
        self.assertEqual(matricula_diario.diario.get_horas_aulas_etapa_1(), 0)
        data = dict(professor_diario=professor_diario.pk, etapa='1', quantidade='8', tipo=1, data=f'01/01/{ano.ano}', conteudo='Aula 01.')
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)

        matricula_diario = MatriculaDiario.objects.get(diario__componente_curricular__componente__descricao=componente)

        self.assertFalse(matricula_diario.is_carga_horaria_diario_fechada())
        self.assertEqual(matricula_diario.get_situacao_frequencia()['rotulo'], 'Cursando')
        self.assertEqual(matricula_diario.get_situacao_nota()['rotulo'], 'Cursando')
        self.assertEqual(matricula_diario.get_situacao_diario()['rotulo'], 'Cursando')
        self.assertEqual(matricula_diario.get_situacao_registrada_diario()['rotulo'], 'Cursando')
        self.assertFalse(matricula_diario.pode_fechar_periodo_letivo())
        self.assertTrue(matricula_diario.is_cursando())
        self.assertFalse(matricula_diario.realizou_todas_avaliacoes_regulares())
        self.assertFalse(matricula_diario.realizou_todas_avaliacoes())
        self.assertFalse(matricula_diario.is_aprovado_sem_prova_final())
        self.assertFalse(matricula_diario.realizou_avaliacao_final())
        self.assertFalse(matricula_diario.is_em_prova_final())
        self.assertFalse(matricula_diario.is_aprovado_em_prova_final())
        self.assertFalse(matricula_diario.is_aprovado_por_nota())
        self.assertTrue(matricula_diario.is_aprovado_por_frequencia())
        self.assertFalse(matricula_diario.is_aprovado())
        self.assertEqual(matricula_diario.get_media_disciplina(), None)
        self.assertEqual(matricula_diario.get_media_final_disciplina(), None)
        self.assertEqual(matricula_diario.get_numero_faltas_primeira_etapa(), 0)
        self.assertEqual(matricula_diario.get_percentual_carga_horaria_frequentada(), 100)
        # lançando mais uma aula para atingir o percentual mínimo de 90% necessário para fechar o diário
        data = dict(professor_diario=professor_diario.pk, etapa='1', quantidade='2', tipo=1, data=f'02/01/{ano.ano}', conteudo='Aula 02.')
        self.client.post(url, data)
        # verificando algumas condições acerca da carga horária
        temp = Diario.locals.get(pk=matricula_diario.diario.pk)
        self.assertEqual(temp.get_horas_aulas_etapa_1(), 10)
        self.assertEqual(temp.get_percentual_carga_horaria_cumprida(), 100)
        matricula_diario = MatriculaDiario.objects.get(pk=matricula_diario.pk)
        self.assertTrue(matricula_diario.is_carga_horaria_diario_fechada())
        self.assertEqual(matricula_diario.get_situacao_frequencia()['rotulo'], 'Aprovado')
        # voltando para a página de listagem de diários
        url = '/edu/meus_diarios/'
        self.client.get(url)
        # acessando a página de visualização de diário na aba "Chamada"
        url = f'/edu/meu_diario/{matricula_diario.diario.pk}/1/?tab=notas_faltas'
        response = self.client.get(url)
        # lançando uma falta
        aula_ = matricula_diario.diario.professordiario_set.all()[0].aula_set.all()[0]
        url_ = f'/edu/registrar_chamada_ajax/{matricula_diario.pk}/{aula_.pk}/1/'
        self.assertContains(response, url, status_code=200)
        response_ = self.client.get(url_)
        self.assertContains(response_, 'OK', status_code=200)

    def acessar_matricula_online(self, contendo=None, contem=True):
        aluno = self.retornar(Aluno)
        if aluno.curso_campus.modalidade.pk == Modalidade.SUBSEQUENTE or aluno.curso_campus.modalidade.pk == Modalidade.CONCOMITANTE:
            return

        if not contendo:
            # Está assim porque nas páginas abaixo o aluno é renderizado com |format que exibe o format_user com o nome usual
            contendo = aluno.pessoa_fisica.nome_usual or aluno.pessoa_fisica.nome

        # acessando a matricula online
        url = ''
        if aluno.matriz.estrutura.tipo_avaliacao == EstruturaCurso.TIPO_AVALIACAO_SERIADO:
            url = f'/edu/pedido_matricula_seriado/{aluno.pk}/'
        elif aluno.matriz.estrutura.tipo_avaliacao == EstruturaCurso.TIPO_AVALIACAO_CREDITO:
            url = f'/edu/pedido_matricula_credito/{aluno.pk}/'

        response = self.client.get(url, follow=True)
        if contem:
            self.assertContains(response, contendo, status_code=200)
        else:
            self.assertNotContains(response, contendo, status_code=200)

    def cadastrar_configuracao_pedido_matricula(self):
        curso = self.retornar(CursoCampus)
        # acessando o admin de configuração de pedido de matrícula
        url = '/admin/edu/configuracaopedidomatricula/'
        response = self.client.get(url)
        self.assertContains(response, 'Renovações de Matrícula', status_code=200)
        # cadastrar configuração de pedido matrícula
        url = '/admin/edu/configuracaopedidomatricula/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Renovação de Matrícula', status_code=200)
        count = ConfiguracaoPedidoMatricula.objects.all().count()
        data = dict(
            descricao='Configuração Seriado 2013.2',
            ano_letivo=self.ano_2013.pk,
            periodo_letivo='2',
            data_inicio=datetime.date.today().strftime("%d/%m/%Y"),
            data_fim=datetime.date.today().strftime("%d/%m/%Y"),
            diretorias=[curso.diretoria.pk],
        )
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(ConfiguracaoPedidoMatricula.objects.all().count(), count + 1)

        # acessando a configuração de pedido de matrícula
        configuracao_pedido_matricula = self.retornar(ConfiguracaoPedidoMatricula)
        url = f'/edu/configuracao_pedido_matricula/{configuracao_pedido_matricula.id}/'
        response = self.client.get(url)
        self.assertContains(response, configuracao_pedido_matricula.descricao, status_code=200)

        # adicionado o curso a configuração de pedido de matrícula
        count = configuracao_pedido_matricula.cursos.count()
        url = f'/edu/add_curso_configuracao_pedido_matricula/{configuracao_pedido_matricula.id}/'
        data = dict(novos_cursos=[curso.pk])
        response = self.client.post(url, data)
        configuracao_pedido_matricula = self.recarregar(configuracao_pedido_matricula)
        self.assertEqual(count, configuracao_pedido_matricula.cursos.count() - 1)

        return configuracao_pedido_matricula

    def acessar_configuracao_pedido_matricula(self, pode_processar=True):
        configuracao_pedido_matricula = self.retornar(ConfiguracaoPedidoMatricula)
        url = f'/edu/configuracao_pedido_matricula/{configuracao_pedido_matricula.pk}/'
        response = self.client.get(url)
        if pode_processar:
            self.assertContains(response, 'Processar Pedidos', status_code=200)
        else:
            self.assertNotContains(response, 'Processar Pedidos', status_code=200)

    def alterando_data_configuracao_para_processar(self):
        configuracao_pedido_matricula = self.retornar(ConfiguracaoPedidoMatricula)
        configuracao_pedido_matricula.data_inicio = datetime.date(2013, 1, 1)
        configuracao_pedido_matricula.data_fim = datetime.date(2013, 1, 31)
        configuracao_pedido_matricula.save()

    def processar_pedidos_matricula(self):
        configuracao_pedido_matricula = self.retornar(ConfiguracaoPedidoMatricula)
        url = f'/edu/processar_pedidos_matricula/{configuracao_pedido_matricula.pk}/'
        response = self.client.get(url, follow=True)
        self.assert_no_validation_errors(response)
        # self.assertContains(response, u'100%')

        url = '{}?continue=1'.format(response.request['PATH_INFO'])
        response = self.client.get(url, follow=True)
        self.assert_no_validation_errors(response)
        # self.assertContains(response, u'Pedidos de matrícula processados com sucesso.', status_code=200)

        aluno = self.retornar(Aluno)
        matricula_periodo = aluno.get_ultima_matricula_periodo()
        self.assertEqual(PedidoMatricula.objects.filter(pedidomatriculadiario__deferido=True).count(), matricula_periodo.matriculadiario_set.count())

    def validando_diarios_com_horarios(self):
        # definindo horario do diário A1
        self.definindo_horario_diario(dias_semana=[4], descricao_componente='A1')
        # definindo horario do diário B1
        self.definindo_horario_diario(dias_semana=[4], descricao_componente='B1')
        # verificando informações
        self.acessar_matricula_online('20132.2.0989.1M', contem=True)
        self.acessar_matricula_online(' B1 ', contem=True)
        self.acessar_matricula_online(' B2 ', contem=False)
        self.acessar_matricula_online(' A1 ', contem=True)
        # definindo horario do diário B2
        self.definindo_horario_diario(dias_semana=[3, 5], descricao_componente='B2')
        # verificando informações, após definição do horário de B2
        self.acessar_matricula_online('20132.2.0989.1M', contem=True)
        self.acessar_matricula_online(' B1 ', contem=True)
        self.acessar_matricula_online(' B2 ', contem=True)
        self.acessar_matricula_online(' A1 ', contem=True)

    def validando_pre_correquisitos(self):
        self.vincular_prerequisito(inserir=True, receptor='B1', pre_requisito='A1')
        self.acessar_matricula_online(' B1 ', contem=False)
        self.acessar_matricula_online(' B2 ', contem=True)
        self.acessar_matricula_online(' A1 ', contem=True)
        self.vincular_correquisito(inserir=True, receptor='B2', correquisito='B1')
        self.acessar_matricula_online(' B1 ', contem=False)
        self.acessar_matricula_online(' B2 ', contem=False)
        self.acessar_matricula_online(' A1 ', contem=True)
        self.vincular_correquisito(inserir=False, receptor='B2', correquisito='B1')
        self.acessar_matricula_online(' B1 ', contem=False)
        self.acessar_matricula_online(' B2 ', contem=True)
        self.acessar_matricula_online(' A1 ', contem=True)
        self.vincular_prerequisito(inserir=False, receptor='B1', pre_requisito='A1')
        self.acessar_matricula_online(' B1 ', contem=True)
        self.acessar_matricula_online(' B2 ', contem=True)
        self.acessar_matricula_online(' A1 ', contem=True)

    def validando_inexistencia_diarios(self):
        self.vincular_correquisito(inserir=True, receptor='B2', correquisito='B1')
        diario_componente_b1 = Diario.objects.filter(componente_curricular__componente__descricao='B1').order_by('-id')[0]
        diario_componente_b1.delete()
        self.acessar_matricula_online(' B1 ', contem=False)
        self.acessar_matricula_online(' B2 ', contem=False)
        self.acessar_matricula_online(' A1 ', contem=True)
        diario_componente_b1.save()
        self.definindo_horario_diario(dias_semana=[4], descricao_componente='B1')
        self.acessar_matricula_online(' B1 ', contem=True)
        self.acessar_matricula_online(' B2 ', contem=True)
        self.acessar_matricula_online(' A1 ', contem=True)

    def validando_exibicao_matricula_vinculo(self):
        self.vincular_prerequisito(inserir=True, receptor='B1', pre_requisito='A1')
        self.vincular_correquisito(inserir=True, receptor='B2', correquisito='B1')
        diario_componente_a1 = Diario.objects.filter(componente_curricular__componente__descricao='A1').order_by('-id')[0]
        diario_componente_a1.delete()
        self.acessar_matricula_online('Para manter o vínculo com a instituição confirme clicando no botão abaixo', contem=True)
        diario_componente_a1.save()
        self.definindo_horario_diario(dias_semana=[4], descricao_componente='A1')
        self.acessar_matricula_online(' B1 ', contem=False)
        self.acessar_matricula_online(' B2 ', contem=False)
        self.acessar_matricula_online(' A1 ', contem=True)
        self.vincular_prerequisito(inserir=False, receptor='B1', pre_requisito='A1')
        self.vincular_correquisito(inserir=False, receptor='B2', correquisito='B1')
        self.acessar_matricula_online(' B1 ', contem=True)
        self.acessar_matricula_online(' B2 ', contem=True)
        self.acessar_matricula_online(' A1 ', contem=True)

    def comprovante_pedido_matricula(self, turma=None, disciplinas=[]):
        pedido_matricula = self.retornar(PedidoMatricula)
        url = f'/edu/comprovante_pedido_matricula/{pedido_matricula.pk}/?html=1'
        response = self.client.get(url)
        if turma:
            self.assertContains(response, turma, status_code=200)
        for disciplina in disciplinas:
            self.assertContains(response, disciplina, status_code=200)

    def acessar_pedidos_matricula(self, conteudo=None):
        url = '/admin/edu/pedidomatriculadiario/'
        response = self.client.get(url)
        if not conteudo:
            conteudo = 'Pedidos de Matrícula'
        self.assertContains(response, conteudo, status_code=200)

    def fluxo_inicial(self, regime):

        # GERAÇÃO DE TURMAS E DIARIOS
        self.vincular_usuario_a_diretoria('Secretário Acadêmico')
        self.vincular_usuario_a_diretoria('Coordenador de Registros Acadêmicos')
        self.acessar_como_secretario()
        self.cadastrar_calendario_academico(tipo=CalendarioAcademico.TIPO_SEMESTRAL)
        self.gerar_turmas_diarios()
        self.cadastrar_professor_nao_servidor()
        self.transferir_posse_etapa()
        self.configurar_diario(diario=self.retornar(Diario, chaves={'componente_curricular__componente__descricao': 'A1'}))
        self.configurar_diario(diario=self.retornar(Diario, chaves={'componente_curricular__componente__descricao': 'A2'}))

        self.acessar_como_professor()
        self.visualizar_locais_horario_aulas_professor()

        # IMPORTAÇÃO DO EDITAL
        self.acessar_como_administrador()
        self.importar_edital()
        self.definir_formas_ingresso()

        # MATRÍCULA INSTITUCIONAL POR PROCESSO SELETIVO
        self.acessar_como_secretario()
        self.identificar_canditado()
        self.efetuar_matricula_institucional()
        self.cancelar_matricula()
        self.identificar_canditado()
        self.efetuar_matricula_institucional()
        self.efetuar_matricula_turma()
        self.emitir_relatorio_alunos()
        self.imprimir_comprovante_matricula()

        self.acessar_como_aluno()
        self.visualizar_dados_pessoais_e_academicos()
        self.atualizar_endereco()
        self.definir_email_institucional()
        self.visualizar_locais_horario_aulas_aluno()

        # LANÇAMENTO DAS NOTAS
        self.acessar_como_professor()
        self.lancar_aulas_faltas_professor(componente='A1')
        self.lancar_aulas_faltas_professor(componente='A2')
        self.imprimir_diario()

        self.acessar_como_aluno()
        self.acompanhar_aulas()

        self.acessar_como_aluno()
        self.visualizar_boletim_individual()

        # ENTREGA DE ETAPA
        self.acessar_como_professor()
        self.lancar_notas_professor(nota=20, descricao_componente='A1')
        self.lancar_notas_professor(nota=90, descricao_componente='A2')
        self.entregar_etapa()

        self.acessar_como_secretario()
        if regime == EstruturaCurso.TIPO_AVALIACAO_SERIADO:
            self.fechar_periodo(
                False,
                SituacaoMatricula.MATRICULADO,
                SituacaoMatriculaPeriodo.DEPENDENCIA,
                MatriculaDiario.SITUACAO_APROVADO,
                componentes_situacoes={'A1': MatriculaDiario.SITUACAO_REPROVADO, 'A2': MatriculaDiario.SITUACAO_APROVADO},
            )
        elif regime == EstruturaCurso.TIPO_AVALIACAO_CREDITO:
            self.fechar_periodo(
                False,
                SituacaoMatricula.MATRICULADO,
                SituacaoMatriculaPeriodo.PERIODO_FECHADO,
                MatriculaDiario.SITUACAO_APROVADO,
                componentes_situacoes={'A1': MatriculaDiario.SITUACAO_REPROVADO, 'A2': MatriculaDiario.SITUACAO_APROVADO},
            )

        # GERANDO TURMAS 2013.2
        self.cadastrar_calendario_academico(self.ano_2013, 2, CalendarioAcademico.TIPO_SEMESTRAL)
        self.gerar_turmas_diarios(ano=self.ano_2013, periodo=2, periodo_matriz=1)

        if regime == EstruturaCurso.TIPO_AVALIACAO_SERIADO:
            self.gerar_turmas_diarios(ano=self.ano_2013, periodo=2, periodo_matriz=2)
        elif regime == EstruturaCurso.TIPO_AVALIACAO_CREDITO:
            self.gerar_turmas_diarios(ano=self.ano_2013, periodo=2, periodo_matriz=2)
            self.gerar_turmas_diarios(ano=self.ano_2013, periodo=2, optativas=True)


class MatriculaOnlineSeriado(MatriculaOnline):
    def setUp(self):
        super().setUp()
        self.initial_data['CursoCampus'] = self.retornar(CursoCampus, chaves={'descricao': 'Mestrado Seriado'})
        self.initial_data['MatrizCurso'] = self.retornar(MatrizCurso, chaves={'matriz__descricao': 'Mestrado', 'curso_campus__descricao': 'Mestrado Seriado'})

    def salvar_pedido_matricula(self, codigo_turma_selecionada=None, descricao_componentes_dependencia_selecionados=[], choque_horario=False):
        aluno = self.retornar(Aluno)
        data = dict()

        # turma selecionada
        if codigo_turma_selecionada:
            turma = Turma.objects.get(codigo=codigo_turma_selecionada)
            data.update({'turma': turma.pk})

        # diários da dependências selecionadas
        for descricao_componente in descricao_componentes_dependencia_selecionados:
            diario = Diario.objects.filter(componente_curricular__componente__descricao=descricao_componente).order_by('-id')[0]
            chave_diario = f'diarios_{diario.componente_curricular.componente.pk}'
            data.update({chave_diario: diario.pk})

        if choque_horario:
            self.definindo_horario_diario(dias_semana=[6], descricao_componente='B1')
            self.definindo_horario_diario(dias_semana=[6], descricao_componente='B2')

        # salvar pedido de matrícula
        count = PedidoMatricula.objects.all().count()
        url = f'/edu/pedido_matricula_seriado/{aluno.pk}/'
        response = self.client.post(url, data)

        if not codigo_turma_selecionada:
            self.assertContains(response, 'Você deve selecionar uma turma.', status_code=200)

        if not descricao_componentes_dependencia_selecionados:
            self.assertContains(response, 'Escolha uma turma para a disciplina em dependência', status_code=200)

        if choque_horario:
            self.assertContains(response, 'Seu pedido não pôde ser salvo, pois há conflitos de horários entre as seguintes disciplinas', status_code=200)
            HorarioAulaDiario.objects.filter(dia_semana=6).delete()

        if codigo_turma_selecionada and descricao_componentes_dependencia_selecionados and not choque_horario:
            self.assert_no_validation_errors(response)
            self.assertEqual(PedidoMatricula.objects.all().count(), count + 1)

    def test_fluxo(self):
        # alterando codigo do curso para utilização do edital já existente
        CursoCampus.objects.filter(codigo='0989').update(codigo='1010', codigo_academico=None)
        CursoCampus.objects.filter(codigo='9999').update(codigo='0989', codigo_academico='0989')

        # MATRICULA ONLINE SERIADO
        self.fluxo_inicial(EstruturaCurso.TIPO_AVALIACAO_SERIADO)

        # CONFIGURAÇÃO DE PEDIDO DE MATRíCULA

        # testando acesso a matricula online sem existir um período de matrícula
        self.acessar_matricula_online('Não existe um período de renovação de matrícula ativa para o seu curso.', contem=True)

        # cadastrando configuracao
        self.cadastrar_configuracao_pedido_matricula()

        # TODO
        # testar cadastro de uma configuração, para um curso, com datas coincidentes
        # testar alteração com pedidos já feitos
        # testar exclusão com não processados
        # testar exclusão com processadas

        # acessando a matricula online
        self.acessar_matricula_online()

        # Validando exibição de diários mediante a definição de horários
        self.validando_diarios_com_horarios()

        # validando pre e correquisitos
        self.validando_pre_correquisitos()

        # validando inexistência de diários
        self.validando_inexistencia_diarios()

        # validando matrícula vínculo
        self.validando_exibicao_matricula_vinculo()

        # validando escolha da turma
        self.salvar_pedido_matricula(descricao_componentes_dependencia_selecionados=['A1'])

        # validando escolha dos diários da disciplina em dependência
        self.salvar_pedido_matricula(codigo_turma_selecionada='20132.2.0989.1M')

        # validando choque de horário
        self.salvar_pedido_matricula('20132.2.0989.1M', ['A1'], choque_horario=True)

        # validando exibição dos Horários das Disciplinas Solicitadas
        self.acessar_matricula_online('Horários das Disciplinas Solicitadas', contem=False)

        # salvando o pedido de matrícula
        self.salvar_pedido_matricula('20132.2.0989.1M', ['A1'])

        # validando exibição dos Horários das Disciplinas Solicitadas
        self.acessar_matricula_online('Horários das Disciplinas Solicitadas', contem=True)

        # validando se o link do comprovante está disponível
        self.acessar_matricula_online('Imprimir Comprovante', contem=True)

        # comprovante de pedido de matrícula
        self.comprovante_pedido_matricula(turma='20132.2.0989.1M', disciplinas=['A1', 'B1', 'B2'])

        # acessando a configuracao e verificando disponibilidade de processar
        self.acessar_configuracao_pedido_matricula(pode_processar=False)
        self.alterando_data_configuracao_para_processar()
        self.acessar_configuracao_pedido_matricula(pode_processar=True)

        # TODO
        # mudança de turma
        # matrículas vínculos
        # dependências
        # segunda chamada

        # processando
        self.processar_pedidos_matricula()

        # acessando pedidos de matrícula
        self.acessar_como_administrador()
        self.acessar_pedidos_matricula(conteudo='20132.2.0989.1M')

        self.acessar_como_aluno()
        self.visualizar_dados_pessoais_e_academicos(ja_selecionou_email=True, com_procedimento_academico=True)


class MatriculaOnlineCredito(MatriculaOnline):
    QTD_ABAIXO_MINIMA = 1
    QTD_MINIMA_DISCIPLINAS = 2
    QTD_MAXIMA_DISCIPLINAS = 3
    CHOQUE_HORARIO = 4

    def setUp(self):
        super().setUp()
        self.initial_data['CursoCampus'] = self.retornar(CursoCampus, chaves={'descricao': 'Mestrado Crédito'})
        self.initial_data['MatrizCurso'] = self.retornar(MatrizCurso, chaves={'matriz__descricao': 'Mestrado', 'curso_campus__descricao': 'Mestrado Crédito'})

    def salvar_pedido_matricula(self, descricao_componentes=[], validacao=None):
        aluno = self.retornar(Aluno)
        estrutura = aluno.matriz.estrutura
        data = dict()

        if validacao:
            # alterando estrutura para validações
            if validacao == self.QTD_ABAIXO_MINIMA:
                estrutura.qtd_minima_disciplinas = 4
            elif validacao == self.QTD_MINIMA_DISCIPLINAS:
                estrutura.qtd_minima_disciplinas = 2
                descricao_componentes.remove('A1')
            elif validacao == self.QTD_MAXIMA_DISCIPLINAS:
                estrutura.numero_disciplinas_superior_periodo = 1
            elif validacao == self.CHOQUE_HORARIO:
                # forcando choque de horário
                self.definindo_horario_diario(dias_semana=[6], descricao_componente='B1')
                self.definindo_horario_diario(dias_semana=[6], descricao_componente='B2')
            estrutura.save()

        # diários selecionados
        for descricao_componente in descricao_componentes:
            diario = Diario.objects.filter(componente_curricular__componente__descricao=descricao_componente).order_by('-id')[0]
            chave_diario = f'diarios_{diario.componente_curricular.componente.pk}'
            data.update({chave_diario: diario.pk})

        # salvar pedido de matrícula
        count = PedidoMatricula.objects.all().count()
        url = f'/edu/pedido_matricula_credito/{aluno.pk}/'
        response = self.client.post(url, data)

        if validacao:
            if validacao == self.QTD_ABAIXO_MINIMA:
                self.assertContains(response, 'O seu curso requer que você se matricule em todas as disciplinas obrigatórias e optativas exibidas.', status_code=200)
            elif validacao == self.QTD_MINIMA_DISCIPLINAS:
                self.assertContains(
                    response,
                    f'Escolha, no mínimo, {estrutura.qtd_minima_disciplinas} disciplina(s) obrigatória(s) e/ou optativa(s) para cursar no próximo período letivo.',
                    status_code=200,
                )
            elif validacao == self.QTD_MAXIMA_DISCIPLINAS:
                self.assertContains(response, 'Não é permitido se matricular em mais de ', status_code=200)
            elif validacao == self.CHOQUE_HORARIO:
                self.assertContains(response, 'Seu pedido não pôde ser salvo, pois há conflitos de horários entre as seguintes disciplinas', status_code=200)
                HorarioAulaDiario.objects.filter(dia_semana=6).delete()

            estrutura.qtd_minima_disciplinas = 1
            estrutura.numero_disciplinas_superior_periodo = 1
            estrutura.save()
        else:
            self.assert_no_validation_errors(response)
            self.assertEqual(PedidoMatricula.objects.all().count(), count + 1)

    def test_fluxo(self):
        # alterando codigo do curso para utilização do edital já existente
        CursoCampus.objects.filter(codigo='0989').update(codigo='1010', codigo_academico=None)
        CursoCampus.objects.filter(codigo='8888').update(codigo='0989', codigo_academico='0989')

        # MATRICULA ONLINE CRÉDITO
        self.fluxo_inicial(EstruturaCurso.TIPO_AVALIACAO_CREDITO)

        # CONFIGURAÇÃO DE PEDIDO DE MATRíCULA

        # testando acesso a matricula online sem existir um período de matrícula
        self.acessar_matricula_online('Não existe um período de renovação de matrícula ativa para o seu curso.', contem=True)

        # cadastrando configuracao
        self.cadastrar_configuracao_pedido_matricula()

        # acessando a matricula online
        self.acessar_matricula_online()

        # TODO
        # eletivas

        # Validando exibição de diários mediante a definição de horários
        self.validando_diarios_com_horarios()

        # validando pre e correquisitos
        self.validando_pre_correquisitos()

        # validando inexistência de diários
        self.validando_inexistencia_diarios()

        # validando matrícula vínculo
        self.validando_exibicao_matricula_vinculo()

        # validando quantidade de diários abaixo da qtd mínima de disciplinas da estrutura
        # self.salvar_pedido_matricula(['A1'], validacao=self.QTD_ABAIXO_MINIMA) TODO

        self.acessar_como_aluno()

        # validando escolha da qtd mínima de disciplinas, quantidade de diários acima da qtd mínima de disciplinas da estrutura
        self.salvar_pedido_matricula(['A1', 'B1'], validacao=self.QTD_MINIMA_DISCIPLINAS)

        # validando escolha da qtd máxima de disciplinas
        self.salvar_pedido_matricula(['A1', 'B1', 'B2', 'OP1'], validacao=self.QTD_MAXIMA_DISCIPLINAS)

        self.acessar_como_secretario()

        # validando choque de horário
        self.salvar_pedido_matricula(['B1', 'B2'], validacao=self.CHOQUE_HORARIO)

        self.acessar_como_aluno()

        # validando exibição dos Horários das Disciplinas Solicitadas
        self.acessar_matricula_online('Horários das Disciplinas Solicitadas', contem=False)

        # salvando o pedido de matrícula
        self.salvar_pedido_matricula(['A1', 'B2'])

        # validando exibição dos Horários das Disciplinas Solicitadas
        self.acessar_matricula_online('Horários das Disciplinas Solicitadas', contem=True)

        # validando se o link do comprovante está disponível
        self.acessar_matricula_online('Imprimir Comprovante', contem=True)

        # comprovante de pedido de matrícula
        self.comprovante_pedido_matricula(disciplinas=['A1', 'B2'])

        self.acessar_como_secretario()

        # acessando a configuracao e verificando disponibilidade de processar
        self.acessar_configuracao_pedido_matricula(pode_processar=False)
        self.alterando_data_configuracao_para_processar()
        self.acessar_configuracao_pedido_matricula(pode_processar=True)

        # TODO
        # matrículas vínculos
        # segunda chamada

        # processando
        self.processar_pedidos_matricula()

        # acessando pedidos de matrícula
        self.acessar_como_administrador()
        self.acessar_pedidos_matricula(conteudo='A1')

        self.acessar_como_aluno()
        self.visualizar_dados_pessoais_e_academicos(ja_selecionou_email=True, com_boletim=False, com_procedimento_academico=True)


class CertificadoENEMTestCase(EduTestCase):
    def setUp(self):
        super().setUp()
        self.initial_data = dict()

        self.servidor_a.user.groups.add(Group.objects.get(name='Administrador Acadêmico'))
        self.servidor_a.user.save()

        self.ano_2013 = Ano.objects.get_or_create(ano=2013)[0]
        self.ano_2014 = Ano.objects.get_or_create(ano=2014)[0]

        # Criando o municipio
        Municipio.objects.get_or_create(identificacao='NATAL-RN')

        uo = self.setor_re_suap.uo
        # Criando o livro
        data = dict(descricao='Livro ENEM', uo=uo, numero_livro=1, folhas_por_livro=1, numero_folha=1, numero_registro=1)
        configuracao_livro = ConfiguracaoLivro.objects.get_or_create(**data)[0]
        configuracao_livro.modalidades.add(self.retornar(Modalidade))

        # Criando o processo para a solicitação do certificado via Processo
        self.processo_a = Processo(vinculo_cadastro=self.servidor_b.get_vinculo(), assunto='Assunto Qualquer', tipo=1, setor_origem=self.servidor_b.setor)
        self.processo_a.save()

        self.acessar_como_administrador()
        data = dict(descricao='Livro ENEM', uo=uo.id, numero_livro=1, folhas_por_livro=1, numero_folha=1, numero_registro=1)
        self.cadastrar(ConfiguracaoLivro, data)

    def test_fluxo(self):
        self.acessar_como_administrador()

        # Cadastrando a configuração de certificação
        url = '/admin/edu/configuracaocertificadoenem/add/'
        response = self.client.get(url)
        arquivo = open('edu/fixtures/test_certificacao_enem.xlsx', 'r+b')
        data = dict(
            ano=self.ano_2014.pk,
            data_primeira_prova='08/11/2014',
            pontuacao_necessaria_areas_conhecimento='450',
            pontuacao_necessaria_redacao='500',
            responsaveis=self.servidor_b.pk,
            planilha_inep=arquivo,
            uo_planilha=self.setor_a0_suap.uo.id,
            numero_portaria='Portaria XYZ',
        )
        response = self.client.post(url, data)
        arquivo.close()
        self.assert_no_validation_errors(response)
        configuracao_certificacao = self.retornar(ConfiguracaoCertificadoENEM)
        self.assertEqual(configuracao_certificacao.registroalunoinep_set.count(), 1)

        # Acessando as configurações para Certificação ENEM
        url = '/admin/edu/configuracaocertificadoenem/'
        response = self.client.get(url)
        self.assertContains(response, configuracao_certificacao.numero_portaria)

        # Acessando a configuração
        url = f'/edu/configuracao_certificacao_enem/{configuracao_certificacao.id}/'
        response = self.client.get(url)
        self.assertContains(response, self.servidor_b.nome)

        # Solicitando um Certificado - Candidato
        self.logout()
        url = '/edu/solicitar_certificado_enem/'
        response = self.client.get(url)
        self.assertContains(response, 'Solicitar Certificado ENEM')

        arquivo_frente = open('edu/static/edu/img/logo_if.jpg', 'r+b')
        arquivo_verso = open('edu/static/edu/img/brazao_republica.jpg', 'r+b')
        data = dict(
            configuracao_certificado_enem=configuracao_certificacao.pk,
            tipo_certificado=2,
            nome='Fulano da Silva',
            cpf='243.887.408-29',
            email='a@a.com',
            confirmacao_email='a@a.com',
            telefone='(84) 3232-3232',
            documento_identidade_frente=arquivo_frente,
            documento_identidade_verso=arquivo_verso,
        )
        response = self.client.post(url, data)
        arquivo_frente.close()
        arquivo_verso.close()
        self.assert_no_validation_errors(response)
        self.assertEqual(SolicitacaoCertificadoENEM.objects.count(), 1)
        solicitacao_certificado = self.retornar(SolicitacaoCertificadoENEM)

        # Atendendo a Solicitação
        self.acessar_como_administrador()
        url = f'/edu/atender_solicitacao_certificado_enem/{solicitacao_certificado.pk}/'
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Registro de emissão de Certificado ENEM cadastrado com sucesso.')
        self.assertEqual(RegistroEmissaoCertificadoENEM.objects.count(), 1)
        registro_emissao = self.retornar(RegistroEmissaoCertificadoENEM)

        # Acessando as solicitações de certificação
        url = '/admin/edu/solicitacaocertificadoenem/'
        response = self.client.get(url)
        self.assertContains(response, "Mostrando 1")

        # Acessando a solicitação de certificação
        url = f'/edu/solicitacao_certificado_enem/{solicitacao_certificado.id}/'
        response = self.client.get(url)
        self.assertContains(response, solicitacao_certificado.nome)

        # Acessando os registros de emissão de certificado
        url = '/admin/edu/registroemissaocertificadoenem/'
        response = self.client.get(url)
        self.assertContains(response, "Mostrando 1")

        # Acessando a solicitação de certificação
        url = f'/edu/registroemissaocertificadoenem/{registro_emissao.id}/'
        response = self.client.get(url)
        self.assertContains(response, solicitacao_certificado.nome)

        # Solicitando um Certificado - Administrador
        url = '/admin/edu/solicitacaocertificadoenem/add/'
        response = self.client.get(url)

        data = dict(
            configuracao_certificado_enem=configuracao_certificacao.pk,
            uo=self.setor_a0_suap.uo_id,
            tipo_certificado=2,
            processo=self.processo_a.pk,
            nome='Beltrano da Silva',
            nome_mae='Beltrana da Silva',
            numero_rg='1234567',
            cpf='478.699.793-50',
            data_nascimento='01/01/1989',
            email='b@b.com',
            telefone='(84) 3232-3232',
            numero_inscricao='0987654321',
            nota_ch='400.10',
            nota_cn='500.40',
            nota_lc='600.30',
            nota_mt='300.60',
            nota_redacao='700.90',
        )
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(SolicitacaoCertificadoENEM.objects.count(), 2)
        solicitacao_certificado = self.retornar(SolicitacaoCertificadoENEM)

        # Rejeitando a Solicitação
        url = f'/edu/rejeitar_solicitacao_certificado_enem/{solicitacao_certificado.pk}/'
        response = self.client.get(url, follow=True)
        data = dict(razao_indeferimento='Justiticativa de teste.')
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Solicitação rejeitada com sucesso.')
