import logging
from collections import OrderedDict

from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils.safestring import mark_safe
from sentry_sdk import capture_exception

from catalogo_provedor_servico.forms import CatalogoEfetuarMatriculaForm, SolicitacaoMatriculaForm
from catalogo_provedor_servico.models import SolicitacaoEtapa, Solicitacao, SolicitacaoEtapaArquivo, \
    SolicitacaoHistoricoSituacao
from catalogo_provedor_servico.providers.base import AbstractBaseServiceProvider, Etapa
from catalogo_provedor_servico.providers.impl.ifrn import codes
from catalogo_provedor_servico.providers.impl.ifrn.codes import IFRN_CODIGO_SIORG
from catalogo_provedor_servico.utils import Notificar, format_data
from comum.models import Ano, Raca
from djtools.utils import httprr
from edu.forms import EfetuarMatriculaForm

from edu.models import Aluno, Cidade, Estado, Pais, OrgaoEmissorRg, Cartorio, NivelEnsino, MatrizCurso
from edu.models.arquivos import AlunoArquivo
from processo_seletivo.models import CandidatoVaga, ausencia_candidato_sinal, matricula_candidato_sinal, \
    inaptidao_candidato_sinal

logger = logging.getLogger(__name__)


class AbstractIfrnServiceProvider(AbstractBaseServiceProvider):

    def get_codigo_siorg(self):
        return IFRN_CODIGO_SIORG


class AbstractMatriculaIFRN(AbstractIfrnServiceProvider):

    def clear_date(self, value):
        if not value:
            return None
        data = str(value).split('-')
        if len(data[0]) == 4:
            return datetime.strptime(value, '%Y-%m-%d').date()
        elif len(data[0]) == 2:
            return datetime.strptime(value, '%d-%m-%Y').date()
        return None

    def clear_value(self, value):
        if value is None or value == 'None':
            return ''
        return str(value)

    def get_candidato_vaga(self, solicitacao):
        etapa_1_dados = SolicitacaoEtapa.objects.get(solicitacao=solicitacao, numero_etapa=1).get_dados_as_json()

        candidato_vaga = None

        for dado in etapa_1_dados['formulario']:
            if dado['name'] == 'candidato_vaga':
                candidato_vaga = dado['value']
                break

        if candidato_vaga is None:
            raise Exception('Erro ao processar requisição')

        return CandidatoVaga.objects.get(pk=candidato_vaga)

    def get_dados_candidato_sgc(self, cpf):
        etapa_1 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=1)
        candidato_vaga = etapa_1.formulario.get_value('candidato_vaga')
        sgc_dados_candidato = CandidatoVaga.matricula_online_dados_candidato(candidato_vaga_id=candidato_vaga)
        return BeautifulSoup(sgc_dados_candidato, 'xml')

    def get_dados_email(self, solicitacao):
        dados_email = list()
        try:
            solicitacao_etapa2 = SolicitacaoEtapa.objects.filter(solicitacao=solicitacao, numero_etapa=2).first()
            if solicitacao_etapa2:
                etapa2 = Etapa.load_from_json(solicitacao_etapa2.get_dados_as_json())
                edital = etapa2.formulario.get_field('edital_nome')
                dados_email.append(edital)
                edital_vaga = etapa2.formulario.get_field('edital_vaga')
                dados_email.append(edital_vaga)
                edital_lista = etapa2.formulario.get_field('edital_lista')
                dados_email.append(edital_lista)
                cpf = etapa2.formulario.get_field('cpf')
                dados_email.append(cpf)
                nome = etapa2.formulario.get_field('nome')
                dados_email.append(nome)
                email_pessoal = etapa2.formulario.get_field('email_pessoal')
                dados_email.append(email_pessoal)
                telefone_govbr = etapa2.formulario.get_field('telefone_govbr')
                dados_email.append(telefone_govbr)

            # Obtém fields com erro
            for numero_etapa in range(1, self.get_numero_total_etapas()):
                solicitacao_etapa = SolicitacaoEtapa.objects.filter(solicitacao=solicitacao, numero_etapa=numero_etapa).first()
                if solicitacao_etapa:
                    etapa = Etapa.load_from_json(solicitacao_etapa.get_dados_as_json())
                    if etapa.formulario.get_campos_by_status(status='ERROR'):
                        dados_email += etapa.formulario.get_campos_by_status(status='ERROR')
            return dados_email
        except Exception as e:
            if settings.DEBUG:
                raise Exception('Detalhes: {}'.format(e))
            capture_exception(e)
            return None

    def get_form(self, candidato_vaga, request, etapa_atual):
        formulario = CatalogoEfetuarMatriculaForm(candidato_vaga=candidato_vaga, request=request)
        etapas = []
        for numero_etapa in range(etapa_atual.numero):
            etapas.append(self._get_etapa_para_edicao(cpf=candidato_vaga.candidato.cpf, numero_etapa=numero_etapa + 1))

        for etapa in etapas + [etapa_atual]:
            if etapa:
                for field in etapa.formulario.campos:
                    value = field["value"]
                    if field['type'] == 'date':
                        value = self.clear_date(value)

                    formulario.data[field['name']] = value
                    formulario.cleaned_data[field['name']] = value
                    # TODO Para avaliar
                    # formulario.fields[field['name']].clean(value)
        return formulario

    def get_idade(self, data_nascimento, data_para_calculo=None):
        if not isinstance(data_nascimento, datetime):
            data_nascimento = datetime(data_nascimento.year, data_nascimento.month, data_nascimento.day)
        hoje = datetime.now()
        _data_para_calculo = data_para_calculo if data_para_calculo else hoje
        num_anos = int((_data_para_calculo - data_nascimento).days / 365.25)
        return num_anos

    def eh_obrigatorio_anexar_reservista(self, data_nascimento):
        '''
        Se tem 18 anos e se a data atual é menor que 30/06: só é obrigatório anexar reservista se completou 18 anos até
        31/12 do ano anterior.
        Maior de 18 anos e menor igual a 45 anos é obrigatório anexar reservista
        Se é menor de 18 anos não é obrigatório anexar reservista
        :param data_nascimento:
        :return: boolean
        '''
        idade = self.get_idade(data_nascimento)
        hoje = datetime.today()
        ano_anterior = (hoje - timedelta(days=365)).year
        utimo_dia_ano_anterior = datetime(ano_anterior, 12, 31, 0, 0)
        retorno = True
        if idade == 18 and hoje.month <= 6:
            if data_nascimento.month <= 6 and not (self.get_idade(data_nascimento, utimo_dia_ano_anterior) >= 18):
                retorno = False
        elif idade < 18:
            retorno = False
        elif idade > 45:
            retorno = False
        return retorno

    def is_em_periodo_avaliacao(self, solicitacao, campus=None):
        se = SolicitacaoEtapa.objects.filter(solicitacao=solicitacao, numero_etapa=1).first()
        if not se:
            return False
        for dado in se.get_dados_as_json()['formulario']:
            if dado['name'] == 'candidato_vaga':
                candidato_vaga = CandidatoVaga.objects.filter(pk=dado['value']).first()
                if not candidato_vaga:
                    return False
                edital = candidato_vaga.candidato.edital
                ver_campus = candidato_vaga.campus
                if campus is not None:
                    ver_campus = campus
                em_periodo_avaliacao = edital.em_periodo_matricula(campus=ver_campus) or edital.em_periodo_avaliacao(campus=ver_campus)
                return em_periodo_avaliacao
        return False

    # TODO: Rever com Hugo essa implementação. A ideia é o service provider não ter estado.
    # Hoje não temos problema porque a cada requisição um novo service provider é instanciado.
    # Acredito que a melhor abordagem é criar uma entidade que represente os dados da inscrição
    # do SGC e criar um método que devolva esta entidade preenchida. Nessa entidade, tentar melhorar
    # a legibilidade, tipo, ao invés "candidato_sgc.criterio_deficiencia", ficaria mais claro algo
    # do tipo "candidato_sgc.tem_deficiencia. Uma vez ajustado aqui, lembrar de replicar o ajuste
    # nos outros providers que usam a mesma informação".
    def set_criterios(self, inscricao):
        self.criterio_etnico = inscricao.lista.criterio_etnico.string == 'True'
        self.criterio_deficiencia = inscricao.lista.criterio_deficiencia.string == 'True'
        self.criterio_escola_publica = inscricao.lista.criterio_escola_publica.string == 'True'
        self.criterio_social = inscricao.lista.criterio_social.string == 'True'
        self.criterio_outros = inscricao.lista.criterio_outros.string == 'True'

    def executar_solicitacao(self, request, solicitacao):
        title = 'Executar Solicitação'
        etapa_1_dados = SolicitacaoEtapa.objects.get(solicitacao=solicitacao, numero_etapa=1).get_dados_as_json()

        candidato_vaga = None

        for dado in etapa_1_dados['formulario']:
            if dado['name'] == 'candidato_vaga':
                candidato_vaga = dado['value']
                break

        if candidato_vaga is None:
            raise Exception('Erro ao processar requisição')

        # TODO: Toda a inteligência para chamar SolicitacaoMatriculaForm praticamente está na variável canditado_vaga.
        # Não seria interessante deixar tudo isso dentro do form?
        candidato_vaga = CandidatoVaga.objects.get(pk=candidato_vaga)

        qs_matriz_curso = MatrizCurso.objects.filter(
            curso_campus=candidato_vaga.oferta_vaga.oferta_vaga_curso.curso_campus).order_by('-id')
        ano_letivo = candidato_vaga.candidato.edital.ano_id
        periodo_letivo = candidato_vaga.candidato.edital.semestre
        turno = candidato_vaga.candidato.turno and candidato_vaga.candidato.turno_id or None
        forma_ingresso = candidato_vaga.oferta_vaga.lista.forma_ingresso and candidato_vaga.oferta_vaga.lista.forma_ingresso.pk or None
        matriz_curso = qs_matriz_curso.exists() and qs_matriz_curso[0].pk or None
        nome = ''
        for etapa in solicitacao.solicitacaoetapa_set.all():
            for field in etapa.get_dados_as_json()['formulario']:
                if field['name'] == 'nome':
                    nome = field['value']
                    break

        initial = dict(
            cpf=candidato_vaga.candidato.cpf,
            nome=nome or candidato_vaga.candidato.nome,
            ano_letivo=ano_letivo,
            periodo_letivo=periodo_letivo,
            turno=turno,
            forma_ingresso=forma_ingresso,
            matriz_curso=matriz_curso,
        )

        form = SolicitacaoMatriculaForm(request.POST or None, candidato_vaga=candidato_vaga, initial=initial)

        if form.is_valid():
            form_matricula = EfetuarMatriculaForm(request=request, candidato_vaga=candidato_vaga)

            data_post = dict()

            for field, value in form.cleaned_data.items():
                if hasattr(value, 'pk'):
                    data_post[field] = value.pk
                else:
                    data_post[field] = value

            for etapa in solicitacao.solicitacaoetapa_set.all():
                for field in etapa.get_dados_as_json()['formulario']:
                    if field['name'] == 'cpf':
                        continue

                    if field['name'] in form_matricula.base_fields:
                        value = field["value"]
                        if field['name'] in ['pai_falecido', 'mae_falecida', 'aluno_especial']:
                            value = False

                        if field['type'] == 'date':
                            value = format_data(value)

                        if field['name'] == 'cidade' and value:
                            cidade = Cidade.objects.filter(pk=value).first()
                            if cidade:
                                data_post['estado'] = str(cidade.estado_id)

                        if field['name'] == 'naturalidade' and value:
                            cidade = Cidade.objects.filter(pk=value).first()
                            if cidade:
                                data_post['estado_naturalidade'] = str(cidade.estado_id)

                        if field['name'] == 'telefone_principal' and not value:
                            for field_telefone_govbr in etapa.get_dados_as_json()['formulario']:
                                if field_telefone_govbr['name'] == 'telefone_govbr':
                                    value = field_telefone_govbr['value']

                        data_post[field['name']] = value

            form_matricula = EfetuarMatriculaForm(request, candidato_vaga, data=data_post)
            if form_matricula.is_valid():
                try:
                    with transaction.atomic():
                        aluno = form_matricula.processar()
                        solicitacao.add_dado_registro_execucao(model_object=aluno, operation='CREATE')

                        try:
                            logger.info('Obtendo foto 3x4 do aluno.')
                            solicitacao_etapa_arquivo_foto = SolicitacaoEtapaArquivo.objects.filter(
                                solicitacao_etapa__solicitacao=solicitacao, nome_atributo_json='foto_3x4')
                            if solicitacao_etapa_arquivo_foto.exists():
                                logger.info('Salvando foto 3x4 no cadastro do aluno.')
                                solicitacao_etapa_arquivo_foto = solicitacao_etapa_arquivo_foto.first()
                                content_file = ContentFile(
                                    solicitacao_etapa_arquivo_foto.arquivo_unico.get_conteudo_as_bytes())
                                aluno.foto.save(solicitacao_etapa_arquivo_foto.nome_original, content_file, save=True)
                                logger.info('Foto 3x4 salva com sucesso.')
                        except Exception as e:
                            logger.error(
                                'Erro ao tentar salvar foto 3x4 no cadastro do aluno. Detalhes: {}'.format(str(e)))
                            capture_exception(e)

                        # TODO: Verificar com equipe se esse teste ainda é necessário
                        if aluno.pessoa_fisica.cpf != candidato_vaga.candidato.cpf:
                            raise ValidationError(
                                'A solicitação não poder ser marcado com "Atendida" pois o CPF do aluno diverge do CPF do solicitante.')

                        # Fazendo o registro de todos os documentos enviados pelo aluno, durante a matrícula, na sua "pasta de documentos".
                        solicitacao_etapa_arquivos = SolicitacaoEtapaArquivo.objects.filter(
                            solicitacao_etapa__solicitacao=solicitacao)
                        if solicitacao_etapa_arquivos.exists():
                            for sea in solicitacao_etapa_arquivos:
                                aluno_etapa_arquivo = AlunoArquivo()

                                observacao = 'Documento fornecido pelo aluno durante matrícula online'
                                if len(observacao) > 255:
                                    observacao = '{} ...'.format(observacao[:250])
                                aluno_etapa_arquivo.observacao = observacao
                                aluno_etapa_arquivo.tipo_origem_cadastro = AlunoArquivo.TIPO_ORIGEM_CADASTRO_MATRICULA_ONLINE

                                aluno_etapa_arquivo.aluno = aluno
                                aluno_etapa_arquivo.arquivo_unico = sea.arquivo_unico
                                aluno_etapa_arquivo.nome_original = sea.nome_original
                                aluno_etapa_arquivo.nome_exibicao = sea.nome_exibicao
                                aluno_etapa_arquivo.descricao = sea.descricao
                                aluno_etapa_arquivo.data_hora_upload = sea.data_hora_upload
                                aluno_etapa_arquivo.save()
                                solicitacao.add_dado_registro_execucao(model_object=aluno_etapa_arquivo, operation='CREATE')

                        # Registra solicitação com ATENDIDA
                        solicitacao.status = Solicitacao.STATUS_ATENDIDO
                        solicitacao.status_detalhamento = f'Matrícula <a href="/edu/aluno/{aluno.matricula}">{aluno.matricula}</a> realizada com sucesso.'
                        solicitacao.save()

                        # Registrando a matricula do aluno junto ao módulo de processo seletivo
                        candidato_vaga.registrar_matricula()
                        solicitacao.add_dado_registro_execucao(model_object=candidato_vaga, operation='UPDATE')

                        # Adicionando link pro aluno no detalhamento sem executar o save da solicitacao
                        Solicitacao.objects.filter(pk=solicitacao.pk).update(status_detalhamento=f'Matrícula <a href="/edu/aluno/{aluno.matricula}">{aluno.matricula}</a> realizada com sucesso.')

                        # Registra acomapanhamento e indica conclusão do serviço junto ao GOVBR
                        self.registrar_acompanhamento(solicitacao)

                        dados_email = self.get_dados_email(solicitacao=solicitacao)

                        # Envia e-mail para aluno com comprovante de matrícula
                        # Este e-mail não esta sendo enviado pelo Notifica Gov.BR pois a plataforma ainda não tem
                        # a funcionalidade de envio de anexo habilitada
                        Notificar.envia_comprovante_matricula(request, dados_email=dados_email, aluno=aluno)

                        # Tenta obter formulário de avaliação do serviço
                        self.obter_formulario_avaliacao(solicitacao)

                        url_avaliacao = None
                        if solicitacao.get_registroavaliacao_govbr():
                            url_avaliacao = solicitacao.get_registroavaliacao_govbr().url_avaliacao

                        Notificar.notifica_conclusao_servico_atendido(solicitacao, dados_email=dados_email,
                                                                      url_avaliacao=url_avaliacao)
                        self.registrar_conclusao(solicitacao)

                        return httprr('/admin/catalogo_provedor_servico/solicitacao/',
                                      mark_safe(f'A solicitação foi atendida com sucesso e gerou a matrícula <a href={aluno.get_absolute_url()}>{aluno.matricula}</a> para o aluno {aluno.pessoa_fisica.nome}.'),
                                      tag='success')

                except IntegrityError:
                    # TODO: Gugu, esse pass é ficar assim mesmo?
                    pass
            else:
                if settings.DEBUG:
                    print(form_matricula.errors)
                    print(form_matricula.non_field_errors())
                for key, value in form_matricula.errors.items():
                    form.errors[key] = value
                form.errors[NON_FIELD_ERRORS] = form_matricula.non_field_errors()

        return locals()


def ausentar_solicitacoes(sender, candidato_vaga_id, desfazer=False, **kwargs):
    campus_zl_id = 14
    if sender == CandidatoVaga:
        try:
            candidato_vaga = CandidatoVaga.objects.filter(pk=candidato_vaga_id).first()
            servico_id = None
            curso_campus = candidato_vaga.oferta_vaga.oferta_vaga_curso.curso_campus
            campus = curso_campus.diretoria.setor.uo.id
            nivel_ensino = curso_campus.modalidade.nivel_ensino.id

            if nivel_ensino == NivelEnsino.MEDIO:
                servico_id = codes.ID_GOVBR_6410_MATRICULA_CURSO_NIVEL_TECNICO_IFRN
            elif nivel_ensino == NivelEnsino.GRADUACAO:
                servico_id = codes.ID_GOVBR_6424_MATRICULA_CURSO_NIVEL_SUPERIOR_IFRN
            elif nivel_ensino == NivelEnsino.POS_GRADUACAO:
                servico_id = codes.ID_GOVBR_10054_MATRICULA_POS_GRADUACAO_IFRN
            elif nivel_ensino == NivelEnsino.FUNDAMENTAL and campus == campus_zl_id:
                servico_id = codes.ID_GOVBR_6176_MATRICULA_EAD

            solicitacoes = Solicitacao.objects.filter(cpf=candidato_vaga.candidato.cpf)

            if servico_id:
                solicitacoes = solicitacoes.filter(servico__id_servico_portal_govbr=servico_id)
                # Coloquei dentro do IF para essa ação não impactar em outros serviços
                if not desfazer:
                    solicitacao = solicitacoes.exclude(status__in=Solicitacao.STATUS_DEFINITIVOS).order_by('id').last()
                    if solicitacao:
                        solicitacao.status = Solicitacao.STATUS_EXPIRADO
                        solicitacao.status_detalhamento = 'A solicitação de matrícula do candidato foi expirada.'
                        solicitacao.save()
                else:
                    solicitacao = solicitacoes.filter(status=Solicitacao.STATUS_EXPIRADO).order_by('id').last()
                    if solicitacao:
                        status = solicitacao.solicitacaohistoricosituacao_set.exclude(status__in=Solicitacao.STATUS_DEFINITIVOS).latest('id').status
                        qs = Solicitacao.objects.filter(pk=solicitacao.pk)
                        qs.update(status=status, status_detalhamento='A Expiração da solicitação foi desfeita.')  # precisa ser feita via update pois o save impede
                        obj = qs.first()  # solicitacao recarregada
                        SolicitacaoHistoricoSituacao.objects.create(
                            solicitacao=obj,
                            status_detalhamento=obj.status_detalhamento,
                            status=status,
                            vinculo_responsavel=obj.vinculo_responsavel
                        )

        except Exception as e:
            capture_exception(e)


ausencia_candidato_sinal.connect(ausentar_solicitacoes)


def matricular_solicitacoes(sender, candidato_vaga_id, desfazer=False, **kwargs):
    campus_zl_id = 14
    if sender == CandidatoVaga:
        try:
            candidato_vaga = CandidatoVaga.objects.filter(pk=candidato_vaga_id).first()
            servico_id = None
            curso_campus = candidato_vaga.oferta_vaga.oferta_vaga_curso.curso_campus
            campus = curso_campus.diretoria.setor.uo.id
            nivel_ensino = curso_campus.modalidade.nivel_ensino.id

            if nivel_ensino == NivelEnsino.MEDIO:
                servico_id = codes.ID_GOVBR_6410_MATRICULA_CURSO_NIVEL_TECNICO_IFRN
            elif nivel_ensino == NivelEnsino.GRADUACAO:
                servico_id = codes.ID_GOVBR_6424_MATRICULA_CURSO_NIVEL_SUPERIOR_IFRN
            elif nivel_ensino == NivelEnsino.POS_GRADUACAO:
                servico_id = codes.ID_GOVBR_10054_MATRICULA_POS_GRADUACAO_IFRN
            elif nivel_ensino == NivelEnsino.FUNDAMENTAL and campus == campus_zl_id:
                servico_id = codes.ID_GOVBR_6176_MATRICULA_EAD

            solicitacoes = Solicitacao.objects.filter(cpf=candidato_vaga.candidato.cpf)

            aluno = Aluno.objects.filter(candidato_vaga=candidato_vaga).first()
            if servico_id:
                solicitacoes = solicitacoes.filter(servico__id_servico_portal_govbr=servico_id)
                # Coloquei dentro do IF para essa ação não impactar em outros serviços
                if not desfazer:
                    solicitacao = solicitacoes.exclude(status__in=Solicitacao.STATUS_DEFINITIVOS).order_by('id').last()
                    if solicitacao:
                        # Registra solicitação com ATENDIDA
                        solicitacao.status = Solicitacao.STATUS_ATENDIDO
                        solicitacao.status_detalhamento = f'Matrícula <a href="/edu/aluno/{aluno.matricula}">{aluno.matricula}</a> realizada com sucesso.'
                        solicitacao.save()

                        # Adicionando link pro aluno no detalhamento sem executar o save da solicitacao
                        Solicitacao.objects.filter(pk=solicitacao.pk).update(status_detalhamento=f'Matrícula <a href="/edu/aluno/{aluno.matricula}">{aluno.matricula}</a> realizada com sucesso.')

                else:
                    solicitacao = solicitacoes.filter(status=Solicitacao.STATUS_ATENDIDO).order_by('id').last()
                    if solicitacao:
                        status = solicitacao.solicitacaohistoricosituacao_set.exclude(status__in=Solicitacao.STATUS_DEFINITIVOS).latest('id').status
                        qs = Solicitacao.objects.filter(pk=solicitacao.pk)
                        qs.update(status=status, status_detalhamento='O atendimento da solicitação foi desfeito.')  # precisa ser feita via update pois o save impede
                        obj = qs.first()  # solicitacao recarregada
                        SolicitacaoHistoricoSituacao.objects.create(
                            solicitacao=obj,
                            status_detalhamento=obj.status_detalhamento,
                            status=status,
                            vinculo_responsavel=obj.vinculo_responsavel
                        )

        except Exception as e:
            capture_exception(e)


matricula_candidato_sinal.connect(matricular_solicitacoes)


def tornar_inaptas_solicitacoes(sender, candidato_vaga_id, desfazer=False, **kwargs):
    campus_zl_id = 14
    if sender == CandidatoVaga:
        try:
            candidato_vaga = CandidatoVaga.objects.filter(pk=candidato_vaga_id).first()
            servico_id = None
            curso_campus = candidato_vaga.oferta_vaga.oferta_vaga_curso.curso_campus
            campus = curso_campus.diretoria.setor.uo.id
            nivel_ensino = curso_campus.modalidade.nivel_ensino.id

            if nivel_ensino == NivelEnsino.MEDIO:
                servico_id = codes.ID_GOVBR_6410_MATRICULA_CURSO_NIVEL_TECNICO_IFRN
            elif nivel_ensino == NivelEnsino.GRADUACAO:
                servico_id = codes.ID_GOVBR_6424_MATRICULA_CURSO_NIVEL_SUPERIOR_IFRN
            elif nivel_ensino == NivelEnsino.POS_GRADUACAO:
                servico_id = codes.ID_GOVBR_10054_MATRICULA_POS_GRADUACAO_IFRN
            elif nivel_ensino == NivelEnsino.FUNDAMENTAL and campus == campus_zl_id:
                servico_id = codes.ID_GOVBR_6176_MATRICULA_EAD

            solicitacoes = Solicitacao.objects.filter(cpf=candidato_vaga.candidato.cpf)

            if servico_id:
                solicitacoes = solicitacoes.filter(servico__id_servico_portal_govbr=servico_id)
                # Coloquei dentro do IF para essa ação não impactar em outros serviços
                if not desfazer:
                    solicitacao = solicitacoes.exclude(status__in=Solicitacao.STATUS_DEFINITIVOS).order_by('id').last()
                    if solicitacao:
                        solicitacao.status = Solicitacao.STATUS_NAO_ATENDIDO
                        solicitacao.status_detalhamento = 'A solicitação de matrícula do candidato não foi atendida.'
                        solicitacao.save()
                else:
                    solicitacao = solicitacoes.filter(status=Solicitacao.STATUS_NAO_ATENDIDO).order_by('id').last()
                    if solicitacao:
                        status = solicitacao.solicitacaohistoricosituacao_set.exclude(status__in=Solicitacao.STATUS_DEFINITIVOS).latest('id').status
                        qs = Solicitacao.objects.filter(pk=solicitacao.pk)
                        qs.update(status=status, status_detalhamento='O não atendimento da solicitação foi desfeito.')  # precisa ser feita via update pois o save impede
                        obj = qs.first()  # solicitacao recarregada
                        SolicitacaoHistoricoSituacao.objects.create(
                            solicitacao=obj,
                            status_detalhamento=obj.status_detalhamento,
                            status=status,
                            vinculo_responsavel=obj.vinculo_responsavel
                        )

        except Exception as e:
            capture_exception(e)


inaptidao_candidato_sinal.connect(tornar_inaptas_solicitacoes)


class BasicoChoicesMixin:

    @staticmethod
    def choices_sim_nao():
        return {'Sim': 'Sim', 'Não': 'Não'}

    @staticmethod
    def choices_ano():
        ano_atual = datetime.now().year
        return Ano.objects.filter(ano__lte=ano_atual).order_by('-ano')


class DocumentoChoicesMixin:

    @staticmethod
    def choices_orgao_emissao_rg():
        return OrgaoEmissorRg.objects.all()

    @staticmethod
    def choices_tipo_certidao():
        choices = OrderedDict()
        for k, v in Aluno.TIPO_CERTIDAO_CHOICES:
            choices[k] = v
        return choices

    @staticmethod
    def choices_cartorio():
        return Cartorio.objects.all()


class EnderecoChoicesMixin:

    @staticmethod
    def choices_estado():
        return Estado.objects.all()

    @staticmethod
    def choices_cidade():
        return Cidade.objects.all()

    @staticmethod
    def choices_pais():
        return Pais.objects.all().exclude(nome='Brasil')

    @staticmethod
    def choices_zona_residencial():
        choices = OrderedDict()
        for k, v in Aluno.TIPO_ZONA_RESIDENCIAL_CHOICES:
            choices[k] = v
        return choices


class EnsinoChoicesMixin:

    @staticmethod
    def choices_nivel_ensino():
        return NivelEnsino.objects.exclude(pk=NivelEnsino.FUNDAMENTAL)

    @staticmethod
    def choices_tipo_instituicao_origem(filters):
        tipo_instituicao = Aluno.TIPO_INSTITUICAO_ORIGEM_CHOICES
        if filters['criterio_escola_publica']:
            tipo_instituicao = [['Pública', 'Pública']]

        choices = OrderedDict()
        for k, v in tipo_instituicao:
            choices[k] = v
        return choices


class NecessidadesEspeciaisChoicesMixin:

    @staticmethod
    def choices_necessidade_especial(filters):
        if filters['criterio_deficiencia']:
            return {'Sim': 'Sim'}
        return {'Sim': 'Sim', 'Não': 'Não'}

    @staticmethod
    def choices_tipo_necessidade_especial():
        choices = OrderedDict()
        for k, v in Aluno.TIPO_NECESSIDADE_ESPECIAL_CHOICES:
            choices[k] = v
        return choices

    @staticmethod
    def choices_tipo_transtorno():
        choices = OrderedDict()
        for k, v in Aluno.TIPO_TRANSTORNO_CHOICES:
            choices[k] = v
        return choices

    @staticmethod
    def choices_superdotacao():
        choices = OrderedDict()
        for k, v in Aluno.SUPERDOTACAO_CHOICES:
            choices[k] = v
        return choices


class PessoalChoicesMixin:

    @staticmethod
    def choices_sexo():
        return {'F': 'Feminino', 'M': 'Masculino'}

    @staticmethod
    def choices_nacionalidade():
        choices = OrderedDict()
        for k, v in Aluno.TIPO_NACIONALIDADE_CHOICES:
            choices[k] = v
        return choices

    @staticmethod
    def choices_estado_civil():
        choices = OrderedDict()
        for k, v in Aluno.ESTADO_CIVIL_CHOICES:
            choices[k] = v
        return choices

    @staticmethod
    def choices_parentesco():
        choices = OrderedDict()
        for k, v in Aluno.PARENTESCO_CHOICES:
            choices[k] = v
        return choices

    @staticmethod
    def choices_tipo_sanguineo():
        choices = OrderedDict()
        for k, v in Aluno.TIPO_SANGUINEO_CHOICES:
            choices[k] = v
        return choices

    @staticmethod
    def choices_raca(filters):
        if filters['criterio_etnico']:
            return Raca.objects.filter(descricao__in=['Parda', 'Preta', 'Indígena'])
        return Raca.objects.all()


class TransporteChoicesMixin:

    @staticmethod
    def choices_poder_publico_responsavel_transporte():
        choices = OrderedDict()
        for k, v in Aluno.PODER_PUBLICO_RESPONSAVEL_TRANSPORTE_CHOICES:
            choices[k] = v
        return choices

    @staticmethod
    def choices_tipo_veiculo():
        choices = OrderedDict()
        for k, v in Aluno.TIPO_VEICULO_CHOICES:
            choices[k] = v
        return choices


class VagaChoicesMixin:

    @staticmethod
    def choices_candidatos_vaga(filters):
        candidato_vagas = CandidatoVaga.matricula_online_disponibilidade(**filters)
        choices = list()
        for obj in candidato_vagas:
            choices.append((obj['candidato_vaga_id'], obj['edital_descricao']))
        return dict(choices)
