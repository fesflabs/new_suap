import logging
from collections import OrderedDict
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from sentry_sdk import capture_exception

from catalogo_provedor_servico.models import Solicitacao, SolicitacaoEtapa, SolicitacaoEtapaArquivo, Servico
from catalogo_provedor_servico.providers.base import Etapa, Mask, GovBr_User_Info
from catalogo_provedor_servico.providers.impl.ifrn.base import AbstractMatriculaIFRN
from catalogo_provedor_servico.providers.impl.ifrn import codes
from comum.models import Ano, Raca
from djtools import forms
from edu.models import Aluno, Pais, Estado, Cidade, NivelEnsino, OrgaoEmissorRg, Cartorio, Modalidade, SituacaoMatricula
from processo_seletivo.models import CandidatoVaga

logger = logging.getLogger(__name__)


class MatriculaTecnicoServiceProvider(AbstractMatriculaIFRN):

    @staticmethod
    def choices_sim_nao():
        return {'Sim': 'Sim', 'Não': 'Não'}

    @staticmethod
    def choices_ano():
        ano_atual = datetime.now().year
        return Ano.objects.filter(ano__lte=ano_atual).order_by('-ano')

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

    @staticmethod
    def choices_nivel_ensino():
        return NivelEnsino.objects.all()

    @staticmethod
    def choices_tipo_instituicao_origem(filters):
        tipo_instituicao = Aluno.TIPO_INSTITUICAO_ORIGEM_CHOICES
        if filters['criterio_escola_publica']:
            tipo_instituicao = [['Pública', 'Pública']]

        choices = OrderedDict()
        for k, v in tipo_instituicao:
            choices[k] = v
        return choices

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

    @staticmethod
    def choices_candidatos_vaga(filters):
        candidato_vagas = CandidatoVaga.matricula_online_disponibilidade(**filters)
        choices = list()
        for obj in candidato_vagas:
            choices.append((obj['candidato_vaga_id'], obj['edital_descricao']))
        return dict(choices)

    # ------------------------------------------------------------------------------------------------------------------

    def get_id_servico_portal_govbr(self):
        return codes.ID_GOVBR_6410_MATRICULA_CURSO_NIVEL_TECNICO_IFRN

    def _validate_dados_etapa(self, request, etapa, solicitacao):
        if etapa.numero == 1:
            candidato_vaga = etapa.formulario.get_value('candidato_vaga')
        else:
            etapa_1 = self._get_etapa_para_edicao(cpf=solicitacao.cpf, numero_etapa=1)
            if etapa_1:
                candidato_vaga = etapa_1.formulario.get_value('candidato_vaga')
            else:
                return ['Falha ao tentar encontrar primeira etapa. Por favor, tente do início novamente.']

        candidato_vaga = CandidatoVaga.objects.get(pk=candidato_vaga)
        form_matricula = self.get_form(candidato_vaga=candidato_vaga, request=request, etapa_atual=etapa)

        # As variáveis comentadas abaixo foram uma tentativa de devolver um dicionário com os erros de validação
        # encontrados do lado provedor, para exibir o erro diretamente no campo em questão.
        # Comentei temporariamente pois algumas validações do wizard do Edu tem que ser revistas.
        # Ex: Caso o aluno seja ESTRANGEIRO, ao inves de vir uma mensagem de erro citando o campo "passaporte",
        # está vindo uma mensagem de erro do campo "nacionalidade".
        has_errors = []
        for field in etapa.formulario.campos:
            try:
                matricula_field = form_matricula.original_fields.get(field['name'], None)
                if hasattr(matricula_field, 'clean'):
                    value = field['value']
                    if value and type(matricula_field) in [forms.DateFieldPlus, forms.DateField]:
                        value = datetime.strptime(value, '%Y-%m-%d').date()
                    matricula_field.clean(value)
            except ValidationError as e:
                has_errors.append(f'<b>{field["label"]}</b> - {e.messages[0]}')

            if hasattr(form_matricula, f"clean_{field['name']}"):
                try:
                    getattr(form_matricula, f"clean_{field['name']}")()
                except ValidationError as e:
                    has_errors.append(f'<b>{field["label"]}</b> - {e.messages[0]}')

        return has_errors

    def _on_persist_solicitacao(self, solicitacao, is_create, is_update):
        if is_create:
            solicitacao.save()

    def _on_persist_solicitacao_etapa(self, etapa, solicitacao_etapa, is_create, is_update):
        if etapa.numero == 2:
            solicitacao = solicitacao_etapa.solicitacao
            candidato_vaga = self.get_candidato_vaga(solicitacao)
            solicitacao.uo = candidato_vaga.candidato.curso_campus.diretoria.setor.uo
            solicitacao.nome = etapa.formulario.get_value('nome')
            solicitacao.save()

    def _on_finish_recebimento_solicitacao(self, solicitacao):
        etapa_1 = self._get_etapa_para_edicao(cpf=solicitacao.cpf, numero_etapa=1)
        etapa_1.formulario.set_avaliacao(name='candidato_vaga', status='OK')
        SolicitacaoEtapa.update_or_create_from_etapa(etapa=etapa_1, solicitacao=solicitacao)

        etapa_7 = self._get_etapa_para_edicao(cpf=solicitacao.cpf, numero_etapa=7)
        etapa_7.formulario.set_avaliacao(name='declaracao_etnia', status='OK')
        etapa_7.formulario.set_avaliacao(name='declaracao_didatica', status='OK')
        etapa_7.formulario.set_avaliacao(name='declaracao_legais', status='OK')
        etapa_7.formulario.set_avaliacao(name='declaracao_veracidade', status='OK')
        etapa_7.formulario.set_avaliacao(name='declaracao_conclusao', status='OK')
        SolicitacaoEtapa.update_or_create_from_etapa(etapa=etapa_7, solicitacao=solicitacao)

    def _get_next_etapa(self, cpf, etapa):
        if etapa.numero == 1:
            return self._get_etapa_2(cpf=cpf)
        if etapa.numero == 2:
            sgc_dados_candidato = self.get_dados_candidato_sgc(cpf)
            self.set_criterios(sgc_dados_candidato.inscricao)
            if self.criterio_social:
                return self._get_etapa_3(cpf=cpf)
            else:
                servico = Servico.objects.get(id_servico_portal_govbr=self.get_id_servico_portal_govbr())
                solicitacao, solicitacao_criada = Solicitacao.objects.get_or_create(
                    servico=servico,
                    cpf=cpf,
                    numero_total_etapas=self.get_numero_total_etapas(),
                    status__in=Solicitacao.STATUS_QUE_PERMITEM_EDICAO_DADOS,
                    defaults={'status': Solicitacao.STATUS_INCOMPLETO, 'status_detalhamento': 'Solicitação Incompleto.'}
                )
                etapa_3 = self._get_etapa_3(cpf=cpf)
                SolicitacaoEtapa.update_or_create_from_etapa(etapa=etapa_3, solicitacao=solicitacao)
                return self._get_etapa_4(cpf=cpf)
        if etapa.numero == 3:
            return self._get_etapa_4(cpf=cpf)
        if etapa.numero == 4:
            return self._get_etapa_5(cpf=cpf)
        if etapa.numero == 5:
            return self._get_etapa_6(cpf=cpf)
        if etapa.numero == 6:
            return self._get_etapa_7(cpf=cpf)

    def _do_avaliacao_disponibilidade_especifica(self, cpf, servico, avaliacao):
        """
        Código utilizado para teste do método
        from catalogo_provedor_servico.providers.base import *
        from catalogo_provedor_servico.providers.factory import *
        from catalogo_provedor_servico.models import *

        cpfs = (('108.795.654-46', 'Caso Hugo'),
                ('115.902.124-44', 'Incompleto'),
                ('011.692.834-46', 'Em Analise'),
                ('701.221.354-07', 'Aguardando Correção'),
                ('107.354.624-10', 'Dados Corrigidos'),
                ('708.338.824-57', 'Atendido'),
                ('706.511.634-47', 'Não Atendido'),
                ('070.003.044-13', 'Ausente'),
                ('039.749.154-94', 'De Hugo'))

        for cpf, tipo in cpfs:
            print('-' * 60)
            print(f'CPF = {cpf}; Tipo = {tipo}')
            servicos = service_provider_factory().get_servicos_disponiveis(cpf)
            print('*' * 60)

        :param cpf:
        :return:
        """
        # Condições para tornar disponível a avaliação
        # 1 - O cidadão está aprovado em um edital que está em peróiodo de matrícula
        # 2 - O cidadão iniciou uma solicitação que está pendente de correção de dados e o edital está dentro do limite de correção
        # 3 - O aluno não poderá ter outro curso de graduação ativo ao mesmo tempo

        alunos_ativos = Aluno.ativos.filter(pessoa_fisica__cpf=cpf, curso_campus__modalidade__nivel_ensino=NivelEnsino.MEDIO)
        avaliacao.add_criterio(not alunos_ativos.exists(), 'Não existe nenhum curso técnico ativo para este CPF', 'Existem um curso técnico ativo para este CPF')

        alunos_trancados = Aluno.objects.filter(pessoa_fisica__cpf=cpf, curso_campus__modalidade__nivel_ensino=NivelEnsino.MEDIO, situacao__in=[SituacaoMatricula.TRANCADO, SituacaoMatricula.TRANCADO_VOLUNTARIAMENTE])
        avaliacao.add_criterio(not alunos_trancados.exists(), 'Não existe nenhum curso técnico com matrícula trancada para este CPF', 'Existe(m) curso(s) técnicos com matrícula trancada para este CPF')

        # Lista contendo todos os candidatos vaga de um cidadão que está em período de matrícula, dentro do limite de correção ou vazio
        candidato_vagas = CandidatoVaga.matricula_online_disponibilidade(cpf=cpf, niveis_ensino=[NivelEnsino.MEDIO])

        em_periodo_matricula = False
        em_periodo_avaliacao = False

        for candidato_vaga in candidato_vagas:
            solicitacoes = Solicitacao.objects.filter(cpf=cpf, servico=servico)  # pode retornar mais de um caso um aluno resolva fazer um curso de mesma modalidade novamente
            solicitacao_anterior = None  # guarda a solicitacao anterior que possui o mesmo candidato vaga

            # calcula se existe uma solução anterior com o mesmo candidato vaga pois
            # solicitacoes para o mesmo cpf e servico mas com candidato vaga diferente eh irrelevante para calcular a disponibilidade
            try:
                for solicitacao in solicitacoes:
                    candidato_vaga_id = candidato_vaga['candidato_vaga_id']
                    candidato_vaga_anterior = solicitacao.solicitacaoetapa_set.get(numero_etapa=1).get_dados_as_json()['formulario'][0]['value']
                    if int(candidato_vaga_anterior) == int(candidato_vaga_id):
                        solicitacao_anterior = solicitacao
                        break
            except Exception as e:
                capture_exception(e)

            # se existir uma solicitacao anterior para o mesmo candidato vaga
            if solicitacao_anterior:
                if candidato_vaga['em_periodo_matricula']:
                    # o periodo de matriculas so estara disponivel para os candidatos em que o status nao seja definitivo
                    em_periodo_matricula = solicitacao_anterior.status not in Solicitacao.STATUS_DEFINITIVOS
                else:
                    # se nao esta em periodo de matricula entao somente os candidatos que aguardam correcao de dados estarão em periodo de avaliacao
                    if solicitacao_anterior.status == Solicitacao.STATUS_AGUARDANDO_CORRECAO_DE_DADOS:
                        em_periodo_avaliacao = True
            else:
                # Se nao houver nenhuma solicitacao anterior para o mesmo candidato vaga entao somente é necessário sabe se o periodo de matricula do candidato vaga existe
                # Nao existe periodo de avaliacao para candidatos que nao tem nenhuma solicitacao anterior para o mesmo candidato vaga
                if candidato_vaga['em_periodo_matricula']:
                    em_periodo_matricula = True

        alunos_ativos_todas_modalidade = Aluno.ativos.filter(pessoa_fisica__cpf=cpf).exclude(curso_campus__modalidade__in=[Modalidade.FIC, Modalidade.PROEJA_FIC_FUNDAMENTAL])

        # Um cidadão Não pode ter mais de 2 matrículas ativas independente da modalidade
        avaliacao.add_criterio(alunos_ativos_todas_modalidade.count() < 2,
                               'Não existem duas ou mais matrículas ativas para este CPF.',
                               'Existem duas ou mais matrículas ativas para este CPF.')

        em_disponibilidade = em_periodo_matricula or em_periodo_avaliacao

        mensagem = ''
        if em_disponibilidade:

            if em_periodo_matricula:
                mensagem = 'Há editais em que o cidadão foi aprovado e o período de matrícula está aberto.'
            elif em_periodo_avaliacao:
                mensagem = 'Há editais em que o cidadão foi aprovado, o período de correção está vigente e sua solicitação em análise.'

        avaliacao.add_criterio(em_disponibilidade, mensagem, 'Não há editais em que o cidadão foi aprovado, ou não estão em período de matrícula nem em período de avaliação.')

    def _get_etapa_1(self, cpf):
        etapa_1 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=1)
        if etapa_1:
            return etapa_1

        etapa_1 = Etapa(numero=1, total_etapas=self.get_numero_total_etapas(), nome='Etapa 1')
        etapa_1.formulario.add_choices(
            label='Edital',
            name='candidato_vaga',
            value=None,
            choices=self.choices_candidatos_vaga,
            filters={'cpf': cpf, 'niveis_ensino': [NivelEnsino.MEDIO]}
        )
        etapa_1.fieldsets.add(name='Dados do Edital', fields=('candidato_vaga',))
        return etapa_1

    def _get_etapa_2(self, cpf):
        etapa_2 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=2)

        if not etapa_2:
            etapa_1 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=1)
            candidato_vaga = CandidatoVaga.objects.get(pk=etapa_1.formulario.get_value('candidato_vaga'))
            sgc_dados_candidato = self.get_dados_candidato_sgc(cpf)

            self.set_criterios(sgc_dados_candidato.inscricao)

            dados_pessoais = sgc_dados_candidato.dados_pessoais
            lista = sgc_dados_candidato.inscricao.lista

            nome_edital = candidato_vaga.candidato.edital.descricao

            estado_value = self.clear_value(dados_pessoais.endereco_uf.string)
            estado_value = Estado.ESTADOS.get(estado_value.upper(), '')

            cidade_value = ''
            value = self.clear_value(dados_pessoais.endereco_municipio.string)
            cidade = Cidade.objects.filter(nome=value.upper(), estado_id=estado_value).first()
            if cidade:
                cidade_value = cidade.pk

            data_nascimento = self.clear_date(dados_pessoais.nascimento_data.string)

            etapa_2 = Etapa(numero=2, total_etapas=self.get_numero_total_etapas(), nome='Etapa 2')

            etapa_2.formulario\
                .add_string(label='Edital', name='edital_nome', value=self.clear_value(nome_edital), read_only=True)\
                .add_string(label='Vaga', name='edital_vaga', value=candidato_vaga.oferta_vaga.oferta_vaga_curso.curso_campus.descricao_historico, read_only=True)\
                .add_string(label='Lista', name='edital_lista', value=self.clear_value(lista.nome.string), read_only=True)
            etapa_2.fieldsets.add(name='Dados do Edital', fields=('edital_nome', 'edital_vaga', 'edital_lista'))

            etapa_2.formulario\
                .add_string(label='CPF', name='cpf', value=self.clear_value(dados_pessoais.cpf.string), read_only=True, mask=Mask.CPF, required=True)\
                .add_choices(label='Nacionalidade', name='nacionalidade', value='', choices=self.choices_nacionalidade, required=True)\
                .add_string(label='Nº do Passaporte', name='passaporte', value='', required=False, max_length=50)
            etapa_2.fieldsets.add(name='Identificação', fields=('cpf', 'nacionalidade', 'passaporte'))

            etapa_2.formulario\
                .add_string(label='Telefone Cadastrado no Gov.BR', name='telefone_govbr', value=None, balcaodigital_user_info=GovBr_User_Info.FONE if not settings.DEBUG else None, required=True, read_only=not settings.DEBUG, max_length=200)\
                .add_string(label='Telefone Principal', name='telefone_principal', value=self.clear_value(dados_pessoais.telefone_residencial.string), required=False, mask=Mask.TELEFONE)\
                .add_string(label='Telefone Secundário', name='telefone_secundario', value=self.clear_value(dados_pessoais.telefone_celular.string), required=False, mask=Mask.TELEFONE)\
                .add_string(label='Telefone do Responsável 1', name='telefone_adicional_1', value='', required=False, mask=Mask.TELEFONE)\
                .add_string(label='Telefone do Responsável 2', name='telefone_adicional_2', value='', required=False, mask=Mask.TELEFONE)\
                .add_string(label='E-mail Pessoal', name='email_pessoal', value='' if settings.DEBUG else self.clear_value(dados_pessoais.email.string), required=True, read_only=not settings.DEBUG)
            etapa_2.fieldsets.add(name='Informações para Contato', fields=('telefone_govbr', 'telefone_principal', 'telefone_secundario', 'telefone_adicional_1', 'telefone_adicional_2', 'email_pessoal'))

            etapa_2.formulario\
                .add_string(label='Nome', name='nome', value=self.clear_value(dados_pessoais.nome.string), required=True, max_length=200)\
                .add_choices(label='Sexo', name='sexo', value=self.clear_value(dados_pessoais.sexo.string), choices=self.choices_sexo, required=True)\
                .add_date(label='Data de Nascimento', name='data_nascimento', value=data_nascimento, mask=Mask.DATE, required=True)\
                .add_choices(label='Estado Civil', name='estado_civil', value=self.clear_value(dados_pessoais.estado_civil.string), choices=self.choices_estado_civil, required=True)\
                .add_file(label='Foto 3x4 recente', name='foto_3x4', value=None, label_to_file='Foto 3x4', allowed_extensions=settings.DEFAULT_UPLOAD_ALLOWED_IMAGE_EXTENSIONS, required=True)
            etapa_2.fieldsets.add(name='Dados Pessoais', fields=('nome', 'sexo', 'data_nascimento', 'estado_civil', 'foto_3x4'))

            etapa_2.formulario\
                .add_string(label='Cep', name='cep', value=self.clear_value(dados_pessoais.endereco_cep.string), required=False, max_length=9, mask=Mask.CEP)\
                .add_string(label='Logradouro', name='logradouro', value=self.clear_value(dados_pessoais.endereco_logradouro.string), required=True)\
                .add_string(label='Número', name='numero', value=self.clear_value(dados_pessoais.endereco_numero.string), required=True)\
                .add_string(label='Complemento', name='complemento', value=self.clear_value(dados_pessoais.endereco_complemento.string), required=False)\
                .add_string(label='Bairro', name='bairro', value=self.clear_value(dados_pessoais.endereco_bairro.string), required=True)\
                .add_choices(label='Cidade', name='cidade', value=cidade_value, choices=self.choices_cidade, required=True)\
                .add_choices(label='Zona Residencial', name='tipo_zona_residencial', value=self.clear_value(dados_pessoais.endereco_zona_residencial.string), choices=self.choices_zona_residencial, required=True)
            etapa_2.fieldsets.add(name='Endereço', fields=('cep', 'logradouro', 'numero', 'complemento', 'cidade', 'bairro', 'tipo_zona_residencial'))

            etapa_2.formulario\
                .add_string(label='Nome do Pai', name='nome_pai', value=self.clear_value(dados_pessoais.pai_nome.string), required=False)\
                .add_choices(label='Estado Civil do Pai', name='estado_civil_pai', value='', choices=self.choices_estado_civil, required=False)\
                .add_boolean(label='Pai Falecido?', name='pai_falecido', value=False, required=False)
            etapa_2.fieldsets.add(name='Dados Familiares - Pai', fields=('nome_pai', 'estado_civil_pai', 'pai_falecido'))

            etapa_2.formulario\
                .add_string(label='Nome da Mãe', name='nome_mae', value=self.clear_value(dados_pessoais.mae_nome.string), required=True)\
                .add_choices(label='Estado Civil da Mãe', name='estado_civil_mae', value='', choices=self.choices_estado_civil, required=False)\
                .add_boolean(label='Mãe Falecida?', name='mae_falecida', value=False, required=False)
            etapa_2.fieldsets.add(name='Dados Familiares - Mãe', fields=('nome_mae', 'estado_civil_mae', 'mae_falecida'))

            etapa_2.formulario\
                .add_string(label='Nome do Responsável', name='responsavel', value='', required=False)\
                .add_string(label='E-mail do Responsável', name='email_responsavel', value='', required=False)\
                .add_choices(label='Parentesco do Responsável', name='parentesco_responsavel', choices=self.choices_parentesco, value='', required=False)\
                .add_string(label='CPF do Responsável', name='cpf_responsavel', value='', mask=Mask.CPF, required=False)
            etapa_2.fieldsets.add(name='Dados Familiares - Responsável', fields=('responsavel', 'email_responsavel', 'parentesco_responsavel', 'cpf_responsavel'))

            if self.criterio_social:
                etapa_2.formulario\
                    .add_integer(label='Número de Membros da Família', name='qtd_membros_familia', value=None, required=True,
                                 min_value=1, help_text='Quantidade de membros da sua família incluindo você mesmo')
                etapa_2.fieldsets.add(name='Dados Familiares - Responsável', fields=('qtd_membros_familia',))
        return etapa_2

    def _get_etapa_3(self, cpf):
        label_duvida = '''<p>1 - Como faço para comprovar a renda da minha família?<br>
                        Anexando a carteira de trabalho OU os 3 últimos contra-cheques do candidato e de todos que residam com o candidato.
                        Atenção: Familiar maior de idade que não trabalhe ou esteja desempregado deve apresentar a carteira de trabalho.</p>

                        <p>2 - Quais paginas da carteira de trabalho devo anexar?<br>
                        Página da foto, verso da foto e páginas do contrato de trabalho. Atenção: Caso a carteira de trabalho esteja desatualizada apresentar os 3 últimos contra cheques.</p>

                        <p>3 - Como incluir o familiar menor de idade no cálculo da renda familiar?<br>
                        Apresentando documento de identificação dele.</p>
                        '''
        help_text = ''' <b><span style="color:red">Atenção:</span> ler atentamente os documentos de renda familiar obrigatórios descritos acima.</b>
        '''
        etapa_2 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=2)

        nome_aluno = etapa_2.formulario.get_value(name='nome')
        data_nascimento = self.clear_date(etapa_2.formulario.get_value(name='data_nascimento'))
        aluno_menor = self.get_idade(data_nascimento) < 18
        try:
            # recupera a quantidade de membros da familia definido na etapa 2
            qtd_membros_familia = int(etapa_2.formulario.get_value('qtd_membros_familia') or 0)
        except Exception as e:
            if settings.DEBUG:
                raise e
            capture_exception(e)
            qtd_membros_familia = 0

        etapa_3 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=3)
        if etapa_3:
            solicitacao_etapa = self._get_solicitacao_etapa(cpf=cpf, numero_etapa=3)
            qtd_arquivos_existentes = len(etapa_3.fieldsets.agrupamentos) - 1

            # se a etapa 3 existir e a quantidade de arquivos existentes for maior que a nova quantidade de membros
            # da família, o excedente de membros da família deverá ser removido
            if qtd_arquivos_existentes > qtd_membros_familia:

                # enumerando os fieldsets e ignorando o primeiro fieldset que é obrigatório
                for qtd, agrupamento in enumerate(etapa_3.fieldsets.agrupamentos[1:]):
                    qtd = qtd + 1
                    # se o número do fieldset for maior que a quantidade de membros da familia ele será removido
                    # juntamente com os campos associados
                    if qtd > qtd_membros_familia:
                        # percorrendo cada campo do fieldset
                        for field in agrupamento['fields'][:]:
                            campo = etapa_3.formulario.get_field(field)
                            if campo['type'] == 'file':
                                # se for do tipo arquivo remove também a SolicitacaoEtapaArquivo do campo
                                SolicitacaoEtapaArquivo.objects.get(
                                    solicitacao_etapa=solicitacao_etapa,
                                    nome_atributo_json=campo['name'],
                                    arquivo_unico__hash_sha512_link_id=campo['value_hash_sha512_link_id']
                                ).delete()
                            etapa_3.formulario.campos.remove(campo)
                        etapa_3.fieldsets.agrupamentos.pop()
                # atualizando a etapa_3 para evitar que os arquivos removidos continuem sendo apontados para o json da etapa
                SolicitacaoEtapa.update_or_create_from_etapa(etapa=etapa_3, solicitacao=solicitacao_etapa.solicitacao)
                return etapa_3

            # se a quantidade de membros da família for igual a quantidade de arquivos existentes simplesmente retorna a etapa
            if qtd_membros_familia == qtd_arquivos_existentes:
                return etapa_3
        else:
            # se a etapa não existe cria e define a quantidade de arquivos existentes como 0
            qtd_arquivos_existentes = 0
            etapa_3 = Etapa(numero=3, total_etapas=self.get_numero_total_etapas(), nome='Etapa 3')
            etapa_3.formulario\
                .add_boolean(label='Documentos de renda familiar obrigatórios?', help_text=label_duvida, name='documentos_renda_obrigatorio', value=bool(qtd_membros_familia), required=False, read_only=True)
            etapa_3.fieldsets.add(name='Documentos de renda familiar obrigatórios', fields=('documentos_renda_obrigatorio',))

        # só chega aqui em dois casos:
        # 1 - caso a quantidade de membros da família seja maior que a quantidade de arquivos existentes
        # 2 - for uma nova etapa nova.
        # se a quantidade de membros da familia for maior que 0, ele deverá gerar dinamicamente a quantidade de novos campos
        if qtd_membros_familia > 0:
            # se a etapa já existir, a quantidade de arquivos já existentes será ignorada na geração dinâmica de novos campos
            for i in range(qtd_arquivos_existentes, qtd_membros_familia):
                # geração dinâmica de novos campos da etapa 3
                field = str(i + 1).zfill(2)
                if i == 0:  # se for o próprio aluno já preenche o nome e o booleano de idade
                    etapa_3.formulario \
                        .add_string(label=f'Nome do {i + 1}º Familiar', name=f'nome_membro_familia_{field}', value=nome_aluno, required=True, read_only=True) \
                        .add_choices(label=f'Parentesco do {i + 1}º Familiar', name=f'parentesco_{field}', choices=self.choices_parentesco, value='', required=False, read_only=True) \
                        .add_file(label=f'Documento Comprovatório do {i + 1}º Familiar', name=f'documento_renda_{field}', value=None, label_to_file=f'Documento de Renda do {i+1}o. Familiar', help_text=help_text, required=True) \
                        .add_boolean(label=f'{i+1}º Familiar Menor de Idade?', name=f'familiar_menor_idade_{field}', value=aluno_menor, required=False, read_only=True)
                    etapa_3.fieldsets.add(name=f'Dados de Renda do {i + 1}º Familiar', fields=(f'nome_membro_familia_{field}', f'parentesco_{field}', f'documento_renda_{field}', f'familiar_menor_idade_{field}'))
                else:
                    etapa_3.formulario\
                        .add_string(label=f'Nome do {i + 1}º Familiar', name=f'nome_membro_familia_{field}', value='', required=True) \
                        .add_choices(label=f'Parentesco do {i + 1}º Familiar', name=f'parentesco_{field}', choices=self.choices_parentesco, value='', required=True) \
                        .add_file(label=f'Documento Comprovatório do {i + 1}º Familiar', name=f'documento_renda_{field}', value=None, label_to_file=f'Documento de Renda do {i + 1}o. Familiar', help_text=help_text, required=True) \
                        .add_boolean(label=f'{i + 1}º Familiar Menor de Idade?', name=f'familiar_menor_idade_{field}', value=False, required=False)
                    etapa_3.fieldsets.add(name=f'Dados de Renda do {i + 1}º Familiar', fields=(f'nome_membro_familia_{field}', f'parentesco_{field}', f'documento_renda_{field}', f'familiar_menor_idade_{field}'))

        return etapa_3

    def _get_etapa_4(self, cpf):
        etapa_4 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=4)

        if not etapa_4:
            sgc_dados_candidato = self.get_dados_candidato_sgc(cpf)

            self.set_criterios(sgc_dados_candidato.inscricao)

            etapa_4 = Etapa(numero=4, total_etapas=self.get_numero_total_etapas(), nome='Etapa 4')

            etapa_4.formulario\
                .add_choices(label='Portador de Necessidades Especiais', name='aluno_pne', value='', choices=self.choices_necessidade_especial, required=True, filters={'criterio_deficiencia': self.criterio_deficiencia})\
                .add_choices(label='Deficiência', name='tipo_necessidade_especial', value='', choices=self.choices_tipo_necessidade_especial, required=False)\
                .add_choices(label='Transtorno', name='tipo_transtorno', value='', choices=self.choices_tipo_transtorno, required=False)\
                .add_choices(label='Superdotação', name='superdotacao', value='', choices=self.choices_superdotacao, required=False)

            if self.criterio_deficiencia:
                etapa_4.formulario\
                    .add_file(label='Cópia de Laudo Médico nos Últimos 12 Meses', name='copia_laudo_medico', value=None, label_to_file='Laudo Médico', required=True)
                etapa_4.fieldsets.add(name='Deficiências, Transtornos e Superdotação', fields=('aluno_pne', 'tipo_necessidade_especial', 'tipo_transtorno', 'superdotacao', 'copia_laudo_medico'))
            else:
                etapa_4.fieldsets.add(name='Deficiências, Transtornos e Superdotação', fields=('aluno_pne', 'tipo_necessidade_especial', 'tipo_transtorno', 'superdotacao'))
        return etapa_4

    def _get_etapa_5(self, cpf):
        etapa_1 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=1)
        candidato_vaga = CandidatoVaga.objects.get(pk=etapa_1.formulario.get_value('candidato_vaga'))

        etapa_5 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=5)

        if not etapa_5:
            etapa_2 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=2)
            sgc_dados_candidato = self.get_dados_candidato_sgc(cpf)
            dados_pessoais = sgc_dados_candidato.dados_pessoais

            self.set_criterios(sgc_dados_candidato.inscricao)

            pais_origem_value = Pais.objects.filter(nome__iexact=self.clear_value(dados_pessoais.nascimento_pais.string))
            if pais_origem_value.exists():
                pais_origem_value = pais_origem_value.first().pk
            else:
                pais_origem_value = ''

            estado_naturalidade_value = Estado.ESTADOS.get(self.clear_value(dados_pessoais.nascimento_uf.string), '')
            naturalidade_value = ''
            if estado_naturalidade_value:
                value = self.clear_value(dados_pessoais.nascimento_municipio.string)
                cidade = Cidade.objects.filter(nome=value.upper(), estado_id=estado_naturalidade_value).first()
                if cidade:
                    naturalidade_value = cidade.pk

            etapa_5 = Etapa(numero=5, total_etapas=self.get_numero_total_etapas(), nome='Etapa 5')

            etapa_5.formulario\
                .add_choices(label='Utiliza Transporte Escolar Público', name='utiliza_transporte_escolar_publico', value='', choices=self.choices_sim_nao, required=False)\
                .add_choices(label='Poder Público Responsável pelo Transporte Escolar', name='poder_publico_responsavel_transporte', value='', choices=self.choices_poder_publico_responsavel_transporte, required=False)\
                .add_choices(label='Tipo de Veículo Utilizado no Transporte Escolar', name='tipo_veiculo', value='', choices=self.choices_tipo_veiculo, required=False)
            etapa_5.fieldsets.add(name='Transporte Escolar Utilizado', fields=('utiliza_transporte_escolar_publico', 'poder_publico_responsavel_transporte', 'tipo_veiculo'))

            etapa_5.formulario\
                .add_choices(label='Tipo Sanguíneo', name='tipo_sanguineo', value='', choices=self.choices_tipo_sanguineo, required=False) \
                .add_file(label='Cópia da Carteira de Vacinação Atualizada', name='copia_carteira_vacinacao', value=None, label_to_file='Carteira de Vacinação', required=False)
            etapa_5.fieldsets.add(name='Informações sobre Saúde', fields=['tipo_sanguineo', 'copia_carteira_vacinacao'])

            fieldset = []

            if etapa_2.formulario.get_value('nacionalidade') != 'Brasileira':
                etapa_5.formulario\
                    .add_choices(label='País de Origem', name='pais_origem', value=pais_origem_value, choices=self.choices_pais, required=False)
                fieldset.append('pais_origem')

            etapa_5.formulario\
                .add_choices(label='Naturalidade', name='naturalidade', value=naturalidade_value, choices=self.choices_cidade, required=False)\
                .add_choices(label='Raça', name='raca', value='', choices=self.choices_raca, required=True, filters={'criterio_etnico': self.criterio_etnico})
            etapa_5.fieldsets.add(name='Outras Informações', fields=['estado_naturalidade', 'naturalidade', 'raca'] + fieldset)

            etapa_5.formulario\
                .add_choices(label='Nível de Ensino', name='nivel_ensino_anterior', value='', choices=self.choices_nivel_ensino, required=True)\
                .add_choices(label='Tipo da Instituição', name='tipo_instituicao_origem', value='', choices=self.choices_tipo_instituicao_origem, required=True, filters={'criterio_escola_publica': self.criterio_escola_publica})\
                .add_choices(label='Ano de Conclusão', name='ano_conclusao_estudo_anterior', value='', choices=self.choices_ano, required=True)
            etapa_5.fieldsets.add(name='Dados Escolares Anteriores', fields=('nivel_ensino_anterior', 'tipo_instituicao_origem', 'ano_conclusao_estudo_anterior'))

            if candidato_vaga.oferta_vaga.oferta_vaga_curso.curso_campus.modalidade_id == Modalidade.SUBSEQUENTE:
                etapa_5.formulario\
                    .add_file(label='Declaração/Certidão/Certificado/Diploma de Ensino Médio', name='copia_doc_conclusao_ensino', value=None, label_to_file='Comprovação de Formação no Ensino Médio', required=True) \
                    .add_file(label='Histórico Escolar do Ensino Médio', name='copia_hist_conclusao_ensino', value=None, label_to_file='Histórico Escolar do Ensino Médio', required=self.criterio_escola_publica) \
                    .add_file(label='Tradução Oficial do Documento, Caso Documento esteja em Língua eestrangeira', name='copia_traducao_documento_escolar', value=None, label_to_file='Tradução Oficial do Documento Escolar', required=False)
                etapa_5.fieldsets.add(name='Documentos Comprobatórios de Escolaridade', fields=('copia_doc_conclusao_ensino', 'copia_hist_conclusao_ensino', 'copia_traducao_documento_escolar'))
            else:
                etapa_5.formulario\
                    .add_file(label='Declaração/Certidão/Certificado/Diploma de Ensino Fundamental', name='copia_doc_conclusao_ensino', value=None, label_to_file='Comprovação de Formação no Ensino Fundamental', required=True) \
                    .add_file(label='Histórico Escolar do Ensino Fundamental', name='copia_hist_conclusao_ensino', value=None, label_to_file='Histórico Escolar do Ensino Fundamental', required=self.criterio_escola_publica) \
                    .add_file(label='Tradução Oficial do Documento, Caso Documento esteja em Língua eestrangeira', name='copia_traducao_documento_escolar', value=None, label_to_file='Tradução Oficial do Documento Escolar', required=False)
                etapa_5.fieldsets.add(name='Documentos Comprobatórios de Escolaridade', fields=('copia_doc_conclusao_ensino', 'copia_hist_conclusao_ensino', 'copia_traducao_documento_escolar'))

        return etapa_5

    def _get_etapa_6(self, cpf):
        etapa_6 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=6)

        if not etapa_6:
            etapa_2 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=2)
            sgc_dados_candidato = self.get_dados_candidato_sgc(cpf)

            dados_pessoais = sgc_dados_candidato.dados_pessoais

            value = self.clear_value(dados_pessoais.rg_uf.string)
            estado_rg_value = Estado.ESTADOS.get(value.upper(), '')

            value = self.clear_value(dados_pessoais.rg_orgao.string)
            value = OrgaoEmissorRg.objects.filter(nome__iexact=value)
            orgao_rg_emissor_value = ''
            if value.exists():
                orgao_rg_emissor_value = value.first().pk

            rg_data_emissao = self.clear_date(dados_pessoais.rg_data_emissao.string)
            data_emissao_titulo_eleitor = ''

            etapa_6 = Etapa(numero=6, total_etapas=self.get_numero_total_etapas(), nome='Etapa 6')

            etapa_6.formulario\
                .add_string(label='Número do RG', name='numero_rg', value=self.clear_value(dados_pessoais.rg_numero.string), required=True)\
                .add_choices(label='Estado Emissor', name='uf_emissao_rg', value=estado_rg_value, choices=self.choices_estado, required=True)\
                .add_choices(label='Orgão Emissor', name='orgao_emissao_rg', value=orgao_rg_emissor_value, choices=self.choices_orgao_emissao_rg, required=True)\
                .add_date(label='Data de Emissão', name='data_emissao_rg', value=rg_data_emissao, mask=Mask.DATE, required=True)\
                .add_file(label='Cópia do RG legível', name='copia_rg', value=None, label_to_file='RG', required=True)
            etapa_6.fieldsets.add(name='RG', fields=('numero_rg', 'uf_emissao_rg', 'orgao_emissao_rg', 'data_emissao_rg', 'copia_rg'))

            data_nascimento = self.clear_date(etapa_2.formulario.get_value(name='data_nascimento'))
            idade = self.get_idade(data_nascimento)

            titulo_eleitor_required = 18 <= idade <= 65
            etapa_6.formulario\
                .add_string(label='Título de Eleitor', name='numero_titulo_eleitor', value='', required=titulo_eleitor_required)\
                .add_string(label='Zona', name='zona_titulo_eleitor', value='', required=titulo_eleitor_required)\
                .add_string(label='Seção', name='secao', value='', required=titulo_eleitor_required)\
                .add_date(label='Data de Emissão', name='data_emissao_titulo_eleitor', mask=Mask.DATE, value=data_emissao_titulo_eleitor, required=titulo_eleitor_required)\
                .add_choices(label='Estado Emissor', name='uf_emissao_titulo_eleitor', value='', choices=self.choices_estado, required=titulo_eleitor_required)\
                .add_file(label='Cópia do Título de Eleitor', name='copia_titulo', value=None, label_to_file='Título de Eleitor', required=titulo_eleitor_required)\
                .add_file(label='Cópia de Quitação Eleitoral', name='copia_quitacao_eleitoral', value=None, label_to_file='Comprovante de Quitação Eleitoral', required=titulo_eleitor_required)
            etapa_6.fieldsets.add(name='Título de Eleitor', fields=('numero_titulo_eleitor', 'zona_titulo_eleitor', 'secao', 'data_emissao_titulo_eleitor', 'uf_emissao_titulo_eleitor', 'copia_titulo', 'copia_quitacao_eleitoral'))

            sexo = etapa_2.formulario.get_value(name='sexo')

            if sexo.upper() == 'M':
                carteira_reservista_required = self.eh_obrigatorio_anexar_reservista(data_nascimento)
                etapa_6.formulario\
                    .add_string(label='Número da Carteira de Reservista', name='numero_carteira_reservista', value='', required=carteira_reservista_required)\
                    .add_string(label='Região', name='regiao_carteira_reservista', value='', required=carteira_reservista_required)\
                    .add_string(label='Série', name='serie_carteira_reservista', value='', required=carteira_reservista_required)\
                    .add_choices(label='Estado Emissor', name='estado_emissao_carteira_reservista', value='', choices=self.choices_estado, required=carteira_reservista_required)\
                    .add_string(label='Ano', name='ano_carteira_reservista', value='', required=carteira_reservista_required)\
                    .add_file(label='Cópia da Carteira de Reservista', name='copia_rervista', value=None, label_to_file='Carteira de Reservista', required=carteira_reservista_required)
                etapa_6.fieldsets.add(name='Carteira de Reservista', fields=('numero_carteira_reservista', 'regiao_carteira_reservista', 'serie_carteira_reservista', 'estado_emissao_carteira_reservista', 'ano_carteira_reservista', 'copia_rervista'))

            etapa_6.formulario.add_choices(label='Tipo de Certidão', name='tipo_certidao', value='', choices=self.choices_tipo_certidao, required=True)\
                .add_choices(label='Cartório', name='cartorio', value='', choices=self.choices_cartorio, required=False)\
                .add_string(label='Número de Termo', name='numero_certidao', value='', required=False)\
                .add_string(label='Folha', name='folha_certidao', value='', required=False)\
                .add_string(label='Livro', name='livro_certidao', value='', required=False)\
                .add_date(label='Data de Emissão', name='data_emissao_certidao', mask=Mask.DATE, value='', required=False)\
                .add_string(label='Matrícula', name='matricula_certidao', value='', required=False)\
                .add_file(label='Cópia da Certidão', name='copia_certidao', value=None, label_to_file='Certidão', required=True)
            etapa_6.fieldsets.add(name='Certidão Civil', fields=('tipo_certidao', 'cartorio', 'numero_certidao', 'folha_certidao', 'livro_certidao', 'data_emissao_certidao', 'matricula_certidao', 'copia_certidao'))

        return etapa_6

    def _get_etapa_7(self, cpf):
        etapa_7 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=7)

        if not etapa_7:
            etapa_1 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=1)
            etapa_2 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=2)
            etapa_5 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=5)
            candidato_vaga = etapa_1.formulario.get_value('candidato_vaga')
            sgc_dados_candidato = self.get_dados_candidato_sgc(cpf)

            self.set_criterios(sgc_dados_candidato.inscricao)

            edital = etapa_1.formulario.get_field('candidato_vaga')
            edital = edital['choices'][int(candidato_vaga)]
            raca = etapa_5.formulario.get_field('raca')
            raca = raca['choices'][int(etapa_5.formulario.get_value('raca'))]

            # Autodeclaração de etnia (apenas para selecionados em PPI)
            pergunta_01 = (
                f'DECLARO que sou uma pessoa <b>{raca}</b>, para o fim específico de atender '
                f'aos termos do <b>{edital}</b> no que se refere à reserva de vagas da lista '
                f'diferenciada com a condição de etnia.'
            )

            data_nascimento = self.clear_date(etapa_2.formulario.get_value(name='data_nascimento'))
            idade = self.get_idade(data_nascimento)

            # Organização didática (para todos)
            pergunta_02 = (
                '<p>Declaro que estou ciente das normas previstas na Organização Didática* do IFRN e que:</p>'
                '<ol>'
                '<li>Terei que frequentar as aulas presenciais, independente do turno, se assim a Instituição determinar;</li>'
                '<li>Terei de renovar minha matrícula, periodicamente, durante o período de renovação de matrícula, previsto no Calendário Acadêmico, sob pena de ter a matrícula cancelada pela instituição;</li>'
                '<li>Caso deixe de frequentar as aulas (acessar o ambiente virtual), nos 10 (dez) primeiros dias úteis do início do curso, sem que seja apresentada uma justificativa, serei desligado do IFRN, sendo minha vaga preenchida por outro candidato, de acordo com a ordem classificatória do processo seletivo.</li>'
                '<li>O estudante não poderá ocupar matrículas simultâneas no mesmo campus ou em diferentes campi do IFRN, nas seguintes situações, independente da modalidade de ensino: em mais de um curso de pós-graduação stricto sensu, em mais de um curso de pós-graduação lato sensu; em mais de um curso de graduação; em mais de um curso técnico de nível médio. Não será permitida a matrícula simultânea em mais de dois cursos.</li>'
                '<li>Para os alunos de graduação, estou ciente da Lei Federal nº 12.089 de 11 de novembro de 2009, que proíbe que uma mesma pessoa ocupe 2 (duas) vagas simultaneamente em instituições públicas de ensino superior.</li>'
                '</ol>'
                '<p>Diante do exposto, assumo o compromisso de seguir as normas institucionais, e peço deferimento.​</p>'
            )

            # Declarações legais
            pergunta_03 = (
                'Declaro, também, estar ciente de que, a comprovação da falsidade desta declaração, em '
                'procedimento que me assegure o contraditório e a ampla defesa, implicará no cancelamento da '
                'minha matrícula nesta Instituição Federal de Ensino, sem prejuízo das sanções penais cabíveis.'
            )

            # Declaração de veracidade
            pergunta_04 = 'Reconheço que as informações prestadas são verdadeiras.'

            # Declaração de conclusão
            pergunta_05 = 'Confirmo que após concluir o meu cadastro não poderei mais alterar os dados e arquivos enviados.'

            # Configura os fields
            etapa_7 = Etapa(numero=7, total_etapas=self.get_numero_total_etapas(), nome='Etapa 7')

            if idade < 18:
                etapa_7.formulario \
                    .add_file(label='Termo de Responsabilidade', name='termo_responsabilidade_menor', value=None, label_to_file='Termo de Responsabilidade', required=True, help_text='<a href="http://suap.ifrn.edu.br/static/edu/documentos/termo-responsabilidade.docx">Baixe o modelo do termo de responsabilidade aqui</a>, então imprima, preencha e assine a mão.') \
                    .add_file(label='Documento com Foto do Responsável', name='documento_responsável', value=None, label_to_file='Documento com Foto do Responsável', required=True)
                etapa_7.fieldsets.add(name='Responsabilidade por Menores de Idade', fields=('termo_responsabilidade_menor', 'documento_responsável'))

            if self.criterio_etnico:
                etapa_7.formulario\
                    .add_boolean(label='Confirmo', help_text=mark_safe(pergunta_01), name='declaracao_etnia', value=None, required=True)
                etapa_7.fieldsets.add(name='Declarações de Autodeclaração de etnia', fields=('declaracao_etnia',))

            etapa_7.formulario\
                .add_boolean(label='Confirmo', help_text=mark_safe(pergunta_02), name='declaracao_didatica', value=None, required=True)
            etapa_7.fieldsets.add(name='Declarações de Organização didática', fields=('declaracao_didatica',))

            etapa_7.formulario\
                .add_boolean(label='Confirmo', help_text=mark_safe(pergunta_03), name='declaracao_legais', value=None, required=True)
            etapa_7.fieldsets.add(name='Declarações legais', fields=('declaracao_legais',))

            etapa_7.formulario\
                .add_boolean(label='Confirmo', help_text=mark_safe(pergunta_04), name='declaracao_veracidade', value=None, required=True)
            etapa_7.fieldsets.add(name='Declaração de veracidade', fields=('declaracao_veracidade',))

            etapa_7.formulario\
                .add_boolean(label='Confirmo', help_text=mark_safe(pergunta_05), name='declaracao_conclusao', value=None, required=True)
            etapa_7.fieldsets.add(name='Declaração de conclusão', fields=('declaracao_conclusao',))

        return etapa_7
