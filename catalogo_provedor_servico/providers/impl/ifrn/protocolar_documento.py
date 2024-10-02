from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from sentry_sdk import capture_exception
from django.utils.html import mark_safe

from catalogo_provedor_servico.forms import PeticaoEletronicaForm
from catalogo_provedor_servico.models import Solicitacao, SolicitacaoEtapa, SolicitacaoEtapaArquivo
from catalogo_provedor_servico.providers.base import Etapa, Mask, GovBr_User_Info
from catalogo_provedor_servico.providers.impl.ifrn.base import AbstractIfrnServiceProvider
from catalogo_provedor_servico.providers.impl.ifrn.codes import ID_GOVBR_10056_PROTOCOLAR_DOCUMENTOS_IFRN
from catalogo_provedor_servico.utils import Notificar
from comum.models import Configuracao
from comum.models import PessoaTelefone
from comum.utils import get_setor
from djtools.utils import httprr
from documento_eletronico.models import Documento, DocumentoDigitalizado, TipoDocumento, HipoteseLegal
from edu.models import Cidade
from processo_eletronico.models import Processo, TipoProcesso, Tramite
from processo_eletronico.views import montar_requerimento_pdf_as_html
from rh.models import UnidadeOrganizacional, PessoaExterna


class ProtocolarDocumentoServiceProvider(AbstractIfrnServiceProvider):

    def get_id_servico_portal_govbr(self):
        return ID_GOVBR_10056_PROTOCOLAR_DOCUMENTOS_IFRN

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
                etapa2 = None
                # Obtém fields com erro da etapa 1 caso exista
                if etapa1.formulario.get_campos_by_status(status='ERROR'):
                    dados_email += etapa1.formulario.get_campos_by_status(status='ERROR')
                solicitacao_etapa2 = SolicitacaoEtapa.objects.get(solicitacao=solicitacao, numero_etapa=1)
                # Obtém fields com erro da etapa 2 caso exista
                if solicitacao_etapa2:
                    etapa2 = Etapa.load_from_json(solicitacao_etapa1.get_dados_as_json())
                if etapa2 and etapa2.formulario.get_campos_by_status(status='ERROR'):
                    dados_email += etapa1.formulario.get_campos_by_status(status='ERROR')
            return dados_email
        except Exception as e:
            if settings.DEBUG:
                raise Exception('Detalhes: {}'.format(e))
            capture_exception(e)

    # def get_next_etapa(self, cpf, etapa):
    #     if etapa.numero == 1:
    #         return self._get_etapa_2(cpf=cpf)
    #     raise Exception('Etapa não implementada.')

    def _on_persist_solicitacao(self, solicitacao, is_create, is_update):
        pass

    def _on_persist_solicitacao_etapa(self, etapa, solicitacao_etapa, is_create, is_update):
        if etapa.numero == 1:
            solicitacao_etapa.solicitacao.nome = etapa.formulario.get_value('nome')
            solicitacao_etapa.solicitacao.save()

        if etapa.numero == 2:
            campus_id = etapa.formulario.get_value('campus')
            solicitacao_etapa.solicitacao.uo = UnidadeOrganizacional.objects.get(pk=campus_id)
            solicitacao_etapa.solicitacao.save()

    def _on_before_finish_recebimento_solicitacao(self, request, solicitacao):
        etapa_1 = self._get_etapa_para_edicao(cpf=solicitacao.cpf, numero_etapa=1)
        if not etapa_1:
            raise Exception('Primeira etapa não encotrada, por favor inicie a solicitação novamente.')
        etapa_1.formulario.set_avaliacao(name='declaracao_ciencia', status='OK')
        SolicitacaoEtapa.update_or_create_from_etapa(etapa=etapa_1, solicitacao=solicitacao)

    @staticmethod
    def choices_unidade_organizacional():
        campi = UnidadeOrganizacional.objects.uo().all()
        data = dict()
        for campus in campi:
            data[campus.pk] = campus.nome.upper()
        return data

    @staticmethod
    def choices_cidade():
        return Cidade.objects.all()

    def _get_etapa_1(self, cpf):
        etapa_1 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=1)
        if etapa_1:
            return etapa_1

        declaracao_ciencia = (
            '<b style="font-size:1.5em">DECLARO QUE ESTOU CIENTE DE QUE ESTE SERVIÇO NÃO TEM POR OBJETIVO A REALIZAÇÃO '
            'DE MATRÍCULA EM PROCESSO SELETIVO OFERTADO PELO IFRN.</b>'
        )

        etapa_1 = Etapa(numero=1, total_etapas=self.get_numero_total_etapas(), nome='Etapa 1')

        etapa_1.formulario\
            .add_boolean(label='Confirmo', help_text=mark_safe(declaracao_ciencia), name='declaracao_ciencia', value=None, required=True)
        etapa_1.fieldsets.add(name='Declaração de Ciência', fields=('declaracao_ciencia',))

        etapa_1.formulario \
            .add_string(label='Nome', name='nome', value=None, balcaodigital_user_info=GovBr_User_Info.NOME, required=True, read_only=True, max_length=200) \
            .add_string(label='CPF', name='cpf', value=None, balcaodigital_user_info=GovBr_User_Info.CPF, mask=Mask.CPF, required=True, read_only=True) \
            .add_string(label='E-mail', name='email', value=None, balcaodigital_user_info=GovBr_User_Info.EMAIL if not settings.DEBUG else None, required=True, read_only=not settings.DEBUG, max_length=200) \
            .add_string(label='Telefone', name='telefone', value=None, balcaodigital_user_info=GovBr_User_Info.FONE if not settings.DEBUG else None, required=True, read_only=not settings.DEBUG, mask=Mask.TELEFONE, max_length=200)
        etapa_1.fieldsets.add(name='Dados Pessoais', fields=('nome', 'cpf', 'email', 'telefone',))

        etapa_1.formulario \
            .add_string(label='Cep', name='cep', value=None, required=False, max_length=9, mask=Mask.CEP) \
            .add_string(label='Logradouro', name='logradouro', value=None, required=True) \
            .add_string(label='Número', name='numero', value=None, required=True) \
            .add_string(label='Complemento', name='complemento', value=None, required=False) \
            .add_string(label='Bairro', name='bairro', value=None, required=True) \
            .add_choices(label='Cidade', name='cidade', value=None, choices=self.choices_cidade, required=True)
        etapa_1.fieldsets.add(name='Endereço', fields=('cep', 'logradouro', 'numero', 'complemento', 'cidade', 'bairro',))

        return etapa_1

    def _get_etapa_2(self, cpf):
        etapa_2 = self._get_etapa_para_edicao(cpf=cpf, numero_etapa=2)
        if etapa_2:
            return etapa_2

        etapa_2 = Etapa(numero=2, total_etapas=self.get_numero_total_etapas(), nome='Etapa 2')
        etapa_2.formulario \
            .add_string(label='Assunto', name='assunto', value=None, required=True, max_length=100) \
            .add_string(label='Descrição', name='descricao', value=None, required=True, max_length=510, widget='textarea') \
            .add_choices(label='Campus', name='campus', value=None, choices=self.choices_unidade_organizacional, required=True)
        etapa_2.fieldsets.add(name='Dados do Requerimento', fields=('assunto', 'descricao', 'campus'))

        for i in range(1, 6):
            etapa_2.formulario \
                .add_string(label='Descrição', name=f'anexo_{i}_descricao', value=None, required=False, max_length=100) \
                .add_file(label='Anexo', name=f'anexo_{i}_file', value=None, label_to_file=f'Anexo{i}', allowed_extensions=['pdf'], required=False)
            etapa_2.fieldsets.add(name=f'Anexo {i}', fields=(f'anexo_{i}_descricao', f'anexo_{i}_file',))

        return etapa_2

    def executar_solicitacao(self, request, solicitacao):
        """

        :param request: Dados do request
        :param solicitacao: Solicitacao de serviço digital que será executada, neste caso cria um proceso eletrônico
        :return: HttpResponse com informação sobre execução (Sucesso, Erro)
        """
        title = 'Solicitação de Protocolo Eletrônico'

        solicitacao_etapa_1 = SolicitacaoEtapa.objects.get(solicitacao=solicitacao, numero_etapa=1)
        etapa_1 = Etapa.load_from_json(solicitacao_etapa_1.get_dados_as_json())

        solicitacao_etapa_2 = SolicitacaoEtapa.objects.get(solicitacao=solicitacao, numero_etapa=2)
        etapa_2 = Etapa.load_from_json(solicitacao_etapa_2.get_dados_as_json())

        campus_id = (etapa_2.formulario.get_value('campus'))
        anexos = list()
        for i in range(1, 6):
            anexo_file = "anexo_{}_file".format(i)
            if etapa_2.formulario.get_field(anexo_file).get('value_hash_sha512_link_id'):
                anexo_descricao = "anexo_{}_descricao".format(i)
                anexos.append({
                    'name': anexo_descricao,
                    'descricao': etapa_2.formulario.get_value(anexo_descricao)
                })

        form = PeticaoEletronicaForm(request.POST or None, request=request, anexos=anexos, campus_id=campus_id)

        if form.is_valid():
            with transaction.atomic():
                nome = etapa_1.formulario.get_value('nome')
                cpf = etapa_1.formulario.get_value('cpf')
                telefone = etapa_1.formulario.get_value('telefone')
                email = etapa_1.formulario.get_value('email')
                assunto = etapa_2.formulario.get_value('assunto')
                descricao = etapa_2.formulario.get_value('descricao')

                # Todo: Falta Refatorar para utilizar o model proxy UsuárioExterno
                pessoa_externa = PessoaExterna.objects.filter(cpf=cpf).first()
                if pessoa_externa:
                    pessoa_externa_created = False
                else:
                    pessoa_externa = PessoaExterna()
                    pessoa_externa.cpf = cpf
                    pessoa_externa_created = True

                pessoa_externa.nome = nome
                pessoa_externa.email = email
                pessoa_externa.save()

                solicitacao.add_dado_registro_execucao(model_object=pessoa_externa, operation='CREATE' if pessoa_externa_created else 'UPDATE')

                pessoa_telefone, pessoa_telefone_created = PessoaTelefone.objects.update_or_create(pessoa=pessoa_externa.pessoa_fisica,
                                                                                                   numero=telefone,
                                                                                                   ramal=''
                                                                                                   )
                solicitacao.add_dado_registro_execucao(model_object=pessoa_telefone, operation='CREATE' if pessoa_telefone_created else 'UPDATE')

                try:
                    tipo_processo = TipoProcesso.objects.get(pk=Configuracao.get_valor_por_chave('processo_eletronico', 'tipo_processo_demanda_externa_do_cidadao'))
                    tipo_documento_requerimento = TipoDocumento.objects.get(pk=Configuracao.get_valor_por_chave('documento_eletronico', 'tipo_documento_requerimento'))
                    hipotese_legal = HipoteseLegal.objects.get(pk=Configuracao.get_valor_por_chave('processo_eletronico', 'hipotese_legal_documento_abertura_requerimento'))
                except Exception:
                    raise ValidationError(
                        'Impossível obter parâmetros de configuação do Sistema: tipo_processo_solicitar_emissao_diploma e/ou tipo_documento_requerimento.'
                        ' Entre em contato com os administradores do sistema.'
                    )

                requerimento_pdf_as_html = montar_requerimento_pdf_as_html(request=request,
                                                                           requerente_nome=nome,
                                                                           requerente_telefone=telefone,
                                                                           requerente_email=email,
                                                                           requerimento_destinatario_setor=form.get_destino(),
                                                                           requerimento_tipo_processo=tipo_processo,
                                                                           requerimento_assunto=assunto,
                                                                           requerimento_descricao=descricao,
                                                                           requerimento_data_hora_emissao=datetime.now(),
                                                                           )

                documento_digitalizado_requerimento = DocumentoDigitalizado.criar(file_content=requerimento_pdf_as_html.content,
                                                                                  file_name='requerimento_externo.html',
                                                                                  tipo_documento=tipo_documento_requerimento,
                                                                                  assunto=assunto,
                                                                                  user=request.user,
                                                                                  papel=form.cleaned_data.get('papel'),
                                                                                  nivel_acesso=Documento.NIVEL_ACESSO_RESTRITO)

                solicitacao.add_dado_registro_execucao(model_object=documento_digitalizado_requerimento, operation='CREATE')

                processo = Processo.criar(tipo_processo=tipo_processo, assunto=assunto,
                                          interessados=[pessoa_externa.pessoa_fisica], hipotese_legal=hipotese_legal)

                documento_digitalizado_processo = processo.adicionar_documento_digitalizado(documento_digitalizado_requerimento)
                solicitacao.add_dado_registro_execucao(model_object=documento_digitalizado_processo, operation='CREATE')

                for i in range(1, 6):
                    nome_atributo_json = "anexo_{}_file".format(i)
                    sea = SolicitacaoEtapaArquivo.objects.filter(solicitacao_etapa__solicitacao=solicitacao,
                                                                 solicitacao_etapa__numero_etapa=2,
                                                                 nome_atributo_json=nome_atributo_json)
                    if sea.exists():
                        sea = sea.first()
                        anexo_tipo = form.cleaned_data.get('anexo_{}_descricao_tipo'.format(i))
                        nivel_acesso = int(form.cleaned_data.get('anexo_{}_descricao_nivel_acesso'.format(i)))
                        anexo_descricao = etapa_2.formulario.get_value('anexo_{}_descricao'.format(i))
                        documento_digitalizado = DocumentoDigitalizado.criar(file_content=sea.arquivo_unico.get_conteudo_as_bytes(),
                                                                             file_name=sea.nome_original,
                                                                             tipo_documento=anexo_tipo,
                                                                             assunto=anexo_descricao,
                                                                             user=request.user,
                                                                             papel=form.cleaned_data.get('papel'),
                                                                             nivel_acesso=nivel_acesso)

                        solicitacao.add_dado_registro_execucao(model_object=documento_digitalizado, operation='CREATE')

                        documento_digitalizado_processo = processo.adicionar_documento_digitalizado(documento_digitalizado)

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
                solicitacao.status_detalhamento = 'Processo {} criado com sucesso.'.format(processo.numero_protocolo_fisico)
                solicitacao.save()

                # Adicionando link pro aprocesso no detalhamento sem executar o save da solicitacao.
                # TODO: Ver uma melhor forma de exibir os dados gerados a partir dessa solicitação, pois esse campo
                # "status_detalhamento" não foi projetado para exibir isso. Uma alternativa que acho interessante
                # é exibir os links a partir do atributo "dados_registros_execucao", que contém todos os objetos
                # criados e ou modificados a partir da solicitaççao.
                Solicitacao.objects.filter(pk=solicitacao.pk).update(
                    status_detalhamento='Processo <a href="{}">{}</a> criado com sucesso.'.format(
                        processo.get_absolute_url(),
                        processo.numero_protocolo_fisico)
                )

                # Registra acomapanhamento e indica conclusão do serviço junto ao GOVBR
                self.registrar_acompanhamento(solicitacao)

                # Enviando o e-mail com a notificação de serviço atendido com sucesso.
                self.obter_formulario_avaliacao(solicitacao)
                dados_email = self.get_dados_email(solicitacao=solicitacao)

                url_avaliacao = None
                if solicitacao.get_registroavaliacao_govbr():
                    url_avaliacao = solicitacao.get_registroavaliacao_govbr().url_avaliacao

                mensagem_principal = '''
                                    A sua solicitação gerou o processo eletrônico número: {},
                                    você pode acompanhar os trâmites do processo na Consulta Pública do  SUAP através do link:
                                    https://suap.ifrn.edu.br/processo_eletronico/consulta_publica/
                                    '''.format(processo.numero_protocolo_fisico)
                Notificar.notifica_conclusao_servico_atendido(solicitacao, dados_email=dados_email, mensagem=mensagem_principal, url_avaliacao=url_avaliacao)
                self.registrar_conclusao(solicitacao)

                return httprr('/admin/catalogo_provedor_servico/solicitacao/',
                              mark_safe(f'A solicitação foi atendida através da criação do processo de número <a href={processo.get_absolute_url()}>{processo.numero_protocolo_fisico}</a>.'),
                              tag='success')

        return locals()
