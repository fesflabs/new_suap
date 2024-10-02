from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.safestring import mark_safe
from sentry_sdk import capture_exception

from catalogo_provedor_servico.models import Solicitacao, SolicitacaoEtapa
from catalogo_provedor_servico.providers.base import Etapa, Mask, \
    GovBr_User_Info
from catalogo_provedor_servico.providers.impl.ifrn.base import AbstractIfrnServiceProvider
from catalogo_provedor_servico.providers.impl.ifrn.codes import ID_GOVBR_6024_EMISSAO_SEGUNDA_VIA_DIPLOMA_IFRN
from catalogo_provedor_servico.utils import Notificar
from comum.models import Configuracao
from comum.utils import get_setor
from djtools.utils import httprr
from documento_eletronico.models import DocumentoDigitalizado, TipoDocumento
from edu.models import Aluno, RegistroEmissaoDiploma
from processo_eletronico.forms import FinalizarRequerimentoForm
from processo_eletronico.models import Processo, TipoProcesso, Tramite
from processo_eletronico.views import montar_requerimento_pdf_as_html


class EmissaoSegundaViaDiplomaServiceProvider(AbstractIfrnServiceProvider):
    @staticmethod
    def choices_alunos(filters):
        alunos = Aluno.objects.filter(**filters).filter(registroemissaodiploma__isnull=False)
        choices = list()
        for obj in alunos:
            choices.append((obj.id, f'{obj.matricula} - {obj.curso_campus.descricao}'))
        return dict(choices)

    def get_id_servico_portal_govbr(self):
        return ID_GOVBR_6024_EMISSAO_SEGUNDA_VIA_DIPLOMA_IFRN

    def _do_avaliacao_disponibilidade_especifica(self, cpf, servico, avaliacao):
        registros = RegistroEmissaoDiploma.objects.filter(aluno__pessoa_fisica__cpf=cpf)
        avaliacao.add_criterio(registros.exists(), f'Existem diplomas emitidos para o aluno com o CPF "{cpf}".',
                               f'O aluno com o CPF "{cpf}" nunca emitiu um diploma.')

    def _get_etapa_1(self, cpf):
        etapa_1 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=1)
        if etapa_1:
            return etapa_1

        etapa_1 = Etapa(numero=1, total_etapas=self.get_numero_total_etapas(), nome='Etapa 1')
        etapa_1.formulario \
            .add_string(label='Nome', name='nome', value=None, balcaodigital_user_info=GovBr_User_Info.NOME, required=True,
                        read_only=True, max_length=200) \
            .add_string(label='CPF', name='cpf', value=None, balcaodigital_user_info=GovBr_User_Info.CPF, mask=Mask.CPF,
                        required=True, read_only=True) \
            .add_string(label='E-mail', name='email', value=None, balcaodigital_user_info=GovBr_User_Info.EMAIL, required=True,
                        read_only=True, max_length=200) \
            .add_string(label='Telefone', name='telefone', value=None, balcaodigital_user_info=GovBr_User_Info.FONE,
                        required=True, read_only=True, max_length=200)
        etapa_1.fieldsets.add(name='Dados Pessoais', fields=('nome', 'cpf', 'email', 'telefone'))

        etapa_1.formulario.add_choices(label='Matrícula', name='alunos', value=None, choices=self.choices_alunos,
                                       filters={'pessoa_fisica__cpf': cpf})
        etapa_1.fieldsets.add(name='Matrícula', fields=('alunos',))
        return etapa_1

    def executar_solicitacao(self, request, solicitacao):
        title = 'Solicitação de Emissão de Segunda via de Diploma'

        form = FinalizarRequerimentoForm(request.POST or None, request=request, sugestao_primeiro_tramite=None)

        if form.is_valid():
            solicitacao_etapa = SolicitacaoEtapa.objects.get(solicitacao=solicitacao, numero_etapa=1)
            dados = Etapa.load_from_json(solicitacao_etapa.get_dados_as_json())
            aluno = Aluno.objects.filter(pk=int(dados.formulario.get_value('alunos'))).first()

            with transaction.atomic():
                try:
                    tipo_processo = TipoProcesso.objects.get(pk=Configuracao.get_valor_por_chave('processo_eletronico',
                                                                                                 'tipo_processo_solicitar_emissao_diploma'))
                    tipo_documento_requerimento = TipoDocumento.objects.get(
                        pk=Configuracao.get_valor_por_chave('documento_eletronico', 'tipo_documento_requerimento'))
                except Exception:
                    raise ValidationError(
                        'Impossível obter parâmetros de configuação do Sistema: tipo_processo_solicitar_emissao_diploma e/ou tipo_documento_requerimento.'
                        ' Entre em contato com os administradores do sistema.'
                    )
                assunto = 'Solicitação de segunda via de diploma'
                processo = Processo.criar(tipo_processo=tipo_processo, assunto=assunto,
                                          interessados=[aluno.pessoa_fisica])

                solicitacao.add_dado_registro_execucao(model_object=processo, operation='CREATE')

                requerimento_pdf_as_html = montar_requerimento_pdf_as_html(request=request,
                                                                           requerente_nome=aluno.pessoa_fisica.nome,
                                                                           requerente_telefone=aluno.telefone_principal,
                                                                           requerente_email=aluno.pessoa_fisica.email,
                                                                           requerimento_destinatario_setor=form.get_destino(),
                                                                           requerimento_tipo_processo=tipo_processo,
                                                                           requerimento_assunto=processo.assunto,
                                                                           requerimento_descricao=processo.assunto,
                                                                           requerimento_data_hora_emissao=datetime.now(),
                                                                           )
                documento_digitalizado_requerimento = DocumentoDigitalizado.criar(
                    file_content=requerimento_pdf_as_html.content,
                    file_name='requerimento_externo.html',
                    tipo_documento=tipo_documento_requerimento,
                    assunto=processo.assunto,
                    user=request.user,
                    papel=form.cleaned_data.get('papel'),
                    nivel_acesso=DocumentoDigitalizado.NIVEL_ACESSO_RESTRITO)

                solicitacao.add_dado_registro_execucao(model_object=documento_digitalizado_requerimento,
                                                       operation='CREATE')

                documento_digitalizado_processo = processo.adicionar_documento_digitalizado(
                    documento_digitalizado_requerimento)

                solicitacao.add_dado_registro_execucao(model_object=documento_digitalizado_processo, operation='CREATE')

                tramite_novo = Tramite()
                tramite_novo.processo = processo
                tramite_novo.tramitar_processo(
                    remetente_setor=get_setor(request.user),
                    remetente_pessoa=request.user.get_profile(),
                    despacho_corpo=None,
                    destinatario_pessoa=None,
                    destinatario_setor=form.get_destino(),
                    assinar_tramite=False,
                    papel=form.cleaned_data.get('papel'),
                )
                solicitacao.add_dado_registro_execucao(model_object=tramite_novo, operation='CREATE')

                solicitacao.status = Solicitacao.STATUS_ATENDIDO
                solicitacao.status_detalhamento = 'Processo {}, para solicitação de emissão de diploma, criado com sucesso.'.format(
                    processo.numero_protocolo_fisico)
                solicitacao.save()

                # Registra acomapanhamento e indica conclusão do serviço junto ao GOVBR
                self.registrar_acompanhamento(solicitacao)
                # self.registrar_conclusao(solicitacao) #Todo: A conslusão vai ser informada após obter url_avaliacao
                # Enviando o e-mail com a notificação de serviço atendido com sucesso.
                self.obter_formulario_avaliacao(solicitacao)
                dados_email = self.get_dados_email(solicitacao=solicitacao)
                url_avaliacao = None
                if solicitacao.get_registroavaliacao_govbr():
                    url_avaliacao = solicitacao.get_registroavaliacao_govbr().url_avaliacao
                mensagem_principal = '''
                                    A sua solicitação gerou o processo eletrônico número: {},
                                    você pode acompanhar os trâmites do processo na Consulta Pública do
                                    <a href="https://suap.ifrn.edu.br/processo_eletronico/consulta_publica/">SUAP</a>
                                    '''.format(processo.numero_protocolo_fisico)
                Notificar.notifica_conclusao_servico_atendido(solicitacao, dados_email=dados_email,
                                                              mensagem=mensagem_principal, url_avaliacao=url_avaliacao)
                return httprr('/admin/catalogo_provedor_servico/solicitacao/',
                              mark_safe(f'A solicitação foi atendida através da criação do processo de número <a href={processo.get_absolute_url()}>{processo.numero_protocolo_fisico}</a>.'),
                              tag='success')

        return locals()

    def is_em_periodo_avaliacao(self, solicitacao, campus=None):
        return True

    def get_dados_email(self, solicitacao):
        dados_email = list()
        try:
            solicitacao_etapa1 = SolicitacaoEtapa.objects.filter(solicitacao=solicitacao, numero_etapa=1).first()
            if solicitacao_etapa1:
                etapa1 = Etapa.load_from_json(solicitacao_etapa1.get_dados_as_json())
                nome = etapa1.formulario.get_field('nome')
                dados_email.append(nome)
                cpf = etapa1.formulario.get_field('cpf')
                dados_email.append(cpf)
                telefone = etapa1.formulario.get_field('telefone')
                dados_email.append(telefone)
                email = etapa1.formulario.get_field('email')
                dados_email.append(email)
                matricula = etapa1.formulario.get_field('alunos')
                dados_email.append(matricula)
                # Obtém fields com erro da etapa 1 caso exista
                if etapa1.formulario.get_campos_by_status(status='ERROR'):
                    dados_email += etapa1.formulario.get_campos_by_status(status='ERROR')
            return dados_email
        except Exception as e:
            if settings.DEBUG:
                raise Exception('Detalhes: {}'.format(e))
            capture_exception(e)
            return None

        return None

    def _on_persist_solicitacao_etapa(self, etapa, solicitacao_etapa, is_create, is_update):
        if etapa.numero == 1:
            aluno = Aluno.objects.filter(pk=int(etapa.formulario.get_value('alunos'))).first()

            if aluno:
                solicitacao_etapa.solicitacao.nome = aluno.pessoa_fisica.nome
                solicitacao_etapa.solicitacao.uo = aluno.campus
                solicitacao_etapa.solicitacao.save()
