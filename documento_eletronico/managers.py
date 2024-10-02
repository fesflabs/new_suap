import operator
from functools import reduce

from django.apps import apps
from django.db import models
from django.db.models.query_utils import Q

from documento_eletronico.status import DocumentoStatus, SolicitacaoStatus
from processo_eletronico.utils import setores_que_sou_chefe_ou_tenho_poder_de_chefe


class PodemClassificarManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(suficiente_para_classificar_processo=True)


class SolicitacaoAssinaturaManager(models.Manager):
    def filter_assinatura_pendente(self, pessoa):
        # Trazendo todas as solicitações para determinada pessoa.
        if not pessoa:
            return self.get_queryset().none()
        solicitacoes = self.get_queryset().filter(solicitado_id=pessoa.id, status=SolicitacaoStatus.STATUS_ESPERANDO)
        qs_filter = [Q(condicionantes__status=SolicitacaoStatus.STATUS_DEFERIDA), Q(condicionantes__isnull=True)]
        solicitacoes = solicitacoes.filter(reduce(operator.or_, qs_filter))
        return solicitacoes

    def filter_requisicao_pendente(self, user):
        return self.get_queryset().filter(solicitante_id=user.id, status=SolicitacaoStatus.STATUS_ESPERANDO)


class SolicitacaoRevisorManager(models.Manager):
    def filter_revisao_pendente(self, pessoa):
        return self.get_queryset().filter(revisor_id=pessoa.id, data_resposta__isnull=True)

    def filter_requisicao_pendente(self, user):
        return self.get_queryset().filter(solicitante_id=user.id, data_resposta__isnull=True)

    def filter_revisados(self, user):
        return self.get_queryset().filter(solicitante_id=user.id, data_resposta__isnull=False, status=SolicitacaoStatus.STATUS_DEFERIDA)


class DocumentoTextoQueryset(models.query.QuerySet):
    def get_model(self):
        return apps.get_model('documento_eletronico', 'DocumentoTexto')

    def pessoais(self):
        return self.filter(setor_dono__isnull=True)

    def impessoais(self):
        return self.filter(setor_dono__isnull=False)

    '''
    Documentos Assinados pelo usuário
    '''

    def assinados(self, user):
        pessoa_fisica_id = user.get_profile().id
        return self.filter(assinaturadocumentotexto__assinatura__pessoa_id=pessoa_fisica_id)

    '''
    Documentos Compartilhados com o usuário ou com os setores do usuário
    '''

    def q_compartilhados(self, user, nivel_permissao=None):
        from documento_eletronico.models import NivelPermissao, CompartilhamentoSetorPessoa

        Documento = self.get_model()

        # Recupera a pessoa física
        pessoa_fisica_id = user.get_profile().id

        # Recupera todos os setores do usuario baseado nas funcoes do servidor
        # Recupera os setores: setores com poder de chefe
        meus_setores_chefe_poder_chefe = setores_que_sou_chefe_ou_tenho_poder_de_chefe(user).values_list('id', flat=True)

        # A partir dos setores recuperados verifica se há algum tipo de compartilhamento com algum deles
        setores_compartilhados_pessoa = CompartilhamentoSetorPessoa.objects.filter(pessoa_permitida_id=pessoa_fisica_id).values_list('setor_dono_id', flat=True)

        if nivel_permissao and nivel_permissao == NivelPermissao.EDITAR:
            setores_compartilhados_pessoa = CompartilhamentoSetorPessoa.objects.filter(pessoa_permitida_id=pessoa_fisica_id, nivel_permissao=nivel_permissao).values_list(
                'setor_dono_id', flat=True
            )
        # COMENTADO PARA CONSIDERAR APENAS AS PERMISSOES EXPLICITAS DO GERENCIAMENTO DE PERMISSOES DE PROCESSO E DOCS
        # - COM ISSO ELE NAO ADICINA A LISTA DE COMPARTILHAMENTO O SETOR SUAP
        # - MESMO QUE O USER TENHA MESMO SETOR SUAP DO DOCUMENTO ELE SO PODE LER SE TIVER PERMISSAO EXPLICITA DO GERENCIAMENTO DE PERMISSOES DE PROCESSO E DOCS
        # - EXCECAO É FEITA PARA SETORES QUE ELE TENHA PODER DE CHEFE OU SEJA CHEFE DE FATO
        # todos_setores = meus_setores + list(setores_compartilhados_setores) + list(setores_compartilhados_pessoa)
        todos_setores = list(meus_setores_chefe_poder_chefe) + list(setores_compartilhados_pessoa)
        # Recuperar todos os documentos compartilhados com o usuário
        if nivel_permissao and nivel_permissao == NivelPermissao.LER:
            query_documento_pessoa_compartilhada = Q(compartilhamento_pessoa_documento__pessoa_permitida_id=pessoa_fisica_id) & (Q(compartilhamento_pessoa_documento__nivel_permissao=NivelPermissao.LER) | Q(compartilhamento_pessoa_documento__nivel_permissao=NivelPermissao.EDITAR))
        elif nivel_permissao:
            query_documento_pessoa_compartilhada = Q(compartilhamento_pessoa_documento__pessoa_permitida_id=pessoa_fisica_id, compartilhamento_pessoa_documento__nivel_permissao=nivel_permissao)
        else:
            query_documento_pessoa_compartilhada = Q(compartilhamento_pessoa_documento__pessoa_permitida_id=pessoa_fisica_id)

        query_setor_compartilhamento = Q(setor_dono_id__in=todos_setores)

        query_sigilo = Q(nivel_acesso=Documento.NIVEL_ACESSO_SIGILOSO)
        query_compartilhamento_documento_nao_sigiloso = Q(~query_sigilo & (query_setor_compartilhamento))
        return [query_documento_pessoa_compartilhada, query_compartilhamento_documento_nao_sigiloso]

    def compartilhados(self, user, nivel_permissao=None):
        qlist = self.q_compartilhados(user, nivel_permissao)
        queryset = reduce(operator.or_, qlist)
        return self.filter(queryset).distinct()

    def vinculados_a_mim(self, user):
        pessoa_fisica_id = user.get_profile().id
        return self.model.objects.filter(interessados__id=pessoa_fisica_id)

    '''
    Documentos que o usuário é o dono
    '''

    def q_proprios(self, user):
        query_dono = Q(usuario_criacao=user)
        # Foi retirado esse trecho pq o query compartilhados ja faz a busca nos setores que ele tem Poder de chefe
        # e o poder de chefe é adicionado toda vez que altera a função do servidor
        # Documento = self.get_model()
        # query_sigilo = Q(nivel_acesso=Documento.NIVEL_ACESSO_SIGILOSO)
        # setores = get_setores_que_sou_chefe_hoje(user)
        # query_setor_dono = Q(setor_dono__in=setores)
        # query_setor = Q(~query_sigilo & query_setor_dono)
        # return [query_dono, query_setor]
        return [query_dono]

    def proprios(self, user):
        return self.filter(reduce(operator.or_, self.q_proprios(user))).distinct()

    '''
        Documentos que o usuário é o dono
    '''

    def q_publicos_assinados(self):
        Documento = self.get_model()
        query_publico = Q(nivel_acesso=Documento.NIVEL_ACESSO_PUBLICO)
        query_finalizado = Q(status=DocumentoStatus.STATUS_FINALIZADO)
        query_publico_assinado = Q(query_publico & query_finalizado)
        return [query_publico_assinado]

    def publicos_assinados(self):
        return self.filter(reduce(operator.or_, self.q_publicos_assinados())).distinct()

    def q_revisao_pendente(self, user):
        query_revisao_pendente = Q(solicitacaorevisao__revisor_id=user.get_profile().id) & Q(solicitacaorevisao__data_resposta__isnull=True)
        return [query_revisao_pendente]

    def revisao_pendente(self, user):
        return self.filter(reduce(operator.or_, self.q_revisao_pendente(user)))

    def q_requisicao_pendente(self, user):
        query_requisicao_pendente = Q(solicitacaorevisao__solicitante_id=user.id) & Q(solicitacaorevisao__data_resposta__isnull=True)
        return [query_requisicao_pendente]

    def requisicao_pendente(self, user):
        return self.filter(reduce(operator.or_, self.q_requisicao_pendente(user)))

    def q_revisados_por(self, user):
        query_revisados = (
            Q(solicitacaorevisao__revisor_id=user.get_profile().id) & Q(solicitacaorevisao__data_resposta__isnull=False) & Q(solicitacaorevisao__status=SolicitacaoStatus.STATUS_DEFERIDA)
        )
        return [query_revisados]

    def revisados_por(self, user):
        return self.filter(reduce(operator.or_, self.q_revisados_por(user)))

    def q_esperando_assinatura(self, user):
        # Verificando as solicitaçoes de assinatura pendentes para o usuário em questão.
        SolicitacaoAssinatura = apps.get_model('documento_eletronico', 'SolicitacaoAssinatura')
        solicitacoes = SolicitacaoAssinatura.objects.filter_assinatura_pendente(user.get_profile())
        query_esperando_assinatura = Q(solicitacaoassinatura__in=solicitacoes)
        return [query_esperando_assinatura]

    def esperando_assinatura(self, user):
        return self.filter(reduce(operator.or_, self.q_esperando_assinatura(user)))

    def q_assinatura_requisitada_por(self, user):
        query_assinatura_requisitada_por = Q(solicitacaoassinatura__solicitante_id=user) & Q(solicitacaoassinatura__data_resposta__isnull=True)
        return [query_assinatura_requisitada_por]

    def assinatura_requisitada_por(self, user):
        return self.filter(reduce(operator.or_, self.q_assinatura_requisitada_por(user)))

    def by_user(self, user):
        return self.filter(
            reduce(
                operator.or_,
                self.q_proprios(user)
                + self.q_compartilhados(user)
                + self.q_publicos_assinados()
                + self.q_revisao_pendente(user)
                + self.q_revisados_por(user)
                + self.q_revisao_pendente(user)
                + self.q_assinatura_requisitada_por(user)
                + self.q_esperando_assinatura(user),
            )
        ).distinct()


class DocumentoTextoManager(models.Manager):
    def get_queryset(self):
        return DocumentoTextoQueryset(self.model, using=self._db)

    def pessoais(self):
        # setor_dono = Documento vinculado a setor (padrao)
        # - aquele que não é um documento pessoal
        return self.get_queryset().pessoais()

    def impessoais(self):
        # setor_dono = Documento vinculado a setor (padrao)
        # - aquele que não é um documento pessoal
        return self.get_queryset().impessoais()

    def assinados(self, user):
        return self.get_queryset().assinados(user)

    def compartilhados(self, user, nivel_permissao=None):
        return self.get_queryset().compartilhados(user, nivel_permissao)

    def by_user(self, user):
        return self.get_queryset().by_user(user)

    def proprios(self, user):
        return self.get_queryset().proprios(user)

    def publicos_assinados(self):
        return self.get_queryset().publicos_assinados()

    def revisao_pendente(self, user):
        return self.get_queryset().revisao_pendente(user)

    def requisicao_pendente(self, user):
        return self.get_queryset().requisicao_pendente(user)

    def revisados_por(self, user):
        return self.get_queryset().revisados_por(user)

    def esperando_assinatura(self, user):
        return self.get_queryset().esperando_assinatura(user)

    def assinatura_requisitada_por(self, user):
        return self.get_queryset().assinatura_requisitada_por(user)

    def vinculados_a_mim(self, user):
        return self.get_queryset().vinculados_a_mim(user)


# Manager usado por entidades que possuem um atributo booleando de nome "ativo".
# Ex: TipoDocumento, ModeloDocumemto.
class AtivosManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(ativo=True)


class AtivosDocumentosPessoaisManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(ativo=True, permite_documentos_pessoais=True)


class DocumentoTextoPessoalQueryset(DocumentoTextoQueryset):
    def get_model(self):
        return apps.get_model('documento_eletronico', 'DocumentoTextoPessoal')

    def q_compartilhados(self, user, nivel_permissao=None):

        # Recupera a pessoa física
        # pessoa_fisica = get_pessoa_fisica(user)
        pessoa_fisica = user.pessoafisica

        # Recuperar todos os documentos compartilhados com o usuário
        query_documento_pessoa_compartilhada = Q(compartilhamento_pessoa_documento__pessoa_permitida_id=pessoa_fisica.id)

        return [query_documento_pessoa_compartilhada]

    def compartilhados(self, user, nivel_permissao=None):
        qs = self.model.objects.none()
        for lookups in self.q_compartilhados(user, nivel_permissao):
            qs = qs | self.filter(lookups)
        return qs.distinct()

    def q_proprios(self, user):
        return [Q(usuario_criacao=user)]


class DocumentoTextoPessoalManager(DocumentoTextoManager):
    def get_queryset(self):
        qs = DocumentoTextoPessoalQueryset(self.model, using=self._db)

        # setor_dono = Documento vinculado a setor (padrao)
        qs = qs.filter(setor_dono__isnull=True)
        return qs


class DocumentoDigitalizadoManager(models.Manager):

    def pessoal(self):
        return super().get_queryset().filter(setor_dono__isnull=False, anexo_simples=False)

    def impessoal(self):
        return super().get_queryset().filter(setor_dono__isnull=True, anexo_simples=False)

    def anexos(self):
        return super().get_queryset().filter(setor_dono__isnull=True, anexo_simples=True)


class DocumentoDigitalizadoPessoalManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(setor_dono__isnull=True, anexo_simples=False)


class DocumentoDigitalizadoAnexoManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(setor_dono__isnull=True, anexo_simples=True)


class AssinaturaDocumentoTextoManager(models.Manager):

    def pessoais(self):
        return self.filter(documento__setor_dono__isnull=True)

    def impessoais(self):
        return self.filter(documento__setor_dono__isnull=False)
