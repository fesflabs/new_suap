from django.core.exceptions import ValidationError
from django.db import transaction
import os
import tempfile
from comum.utils import tl
from djtools.db import models
from edu.models.alunos import Aluno
from edu.models.logs import LogModel
from rh.models import AbstractVinculoArquivoUnico, ArquivoUnico


class TipoAlunoArquivo(models.ModelPlus):
    SEARCH_FIELDS = ['nome']

    DOC_RENDA = 40
    LAUDO_PCD = 41

    OUTROS = 'Outros'
    IDENTIDADE = 'Documento de Identidade'
    HISTORICO = 'Histórico Escolar'
    CERTIDAO_NASCIMENTO = 'Certidão de Nascimento'
    CERTIDAO_CASAMENTO = 'Certidão de Casamento'
    TITULO_ELEITOR = 'Título de Eleitor'

    nome = models.CharFieldPlus(
        'Nome', max_length=120, unique=True, null=False, blank=False)
    # campos_servicos = models.ManyToManyFieldPlus('catalogo_provedor_servico.CampoServico', verbose_name='Campos Correlacionados dos serviços de matrícula', blank=True)
    ativo = models.BooleanField('Ativo?', default=True, null=False, blank=False)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Tipo de Documento da Pasta Documental'
        verbose_name_plural = 'Tipos de Documentos da Pasta Documental'

    def __str__(self):
        return self.nome


class GrupoArquivoObrigatorio(LogModel):
    descricao = models.CharFieldPlus(verbose_name='Descrição')
    modalidades = models.ManyToManyFieldPlus('edu.Modalidade', verbose_name='Modalidades')
    tipos = models.ManyToManyFieldPlus(TipoAlunoArquivo, verbose_name='Tipos de Documentos')

    class Meta:
        verbose_name = 'Grupo de Arquivos Obrigatórios'
        verbose_name_plural = 'Grupo de Arquivos Obrigatórios'
        ordering = 'descricao',

    def __str__(self):
        return self.descricao


class AlunoArquivo(AbstractVinculoArquivoUnico, LogModel):
    tipo = models.ForeignKeyPlus(TipoAlunoArquivo)
    aluno = models.ForeignKeyPlus(Aluno, on_delete=models.CASCADE)

    validado = models.BooleanField('Validado', default=True, null=True)
    data_validacao = models.DateTimeFieldPlus('Data da Validação', null=True)
    responsavel_validacao = models.ForeignKeyPlus('comum.User', verbose_name='Responsável pela Validação', null=True)

    observacao = models.TextField(verbose_name='Observação', max_length=255, blank=True, null=True)

    em_diploma = models.BooleanField(verbose_name='Contido no diploma vigente', default=False, null=False, blank=False)

    TIPO_ORIGEM_CADASTRO_MANUAL = 'MANUAL'
    TIPO_ORIGEM_CADASTRO_MATRICULA_ONLINE = 'MATRICULA_ONLINE'
    TIPO_ORIGEM_CADASTRO_CHOICES = (
        (TIPO_ORIGEM_CADASTRO_MANUAL, 'Manual'),
        (TIPO_ORIGEM_CADASTRO_MATRICULA_ONLINE, 'Matrícula Online'),
    )
    tipo_origem_cadastro = models.CharField('Tipo de Origem do Cadastro', max_length=25, choices=TIPO_ORIGEM_CADASTRO_CHOICES, editable=False)

    class Meta:
        verbose_name = 'Arquivo do Aluno'
        verbose_name_plural = 'Arquivos do Aluno'
        ordering = ('-data_hora_upload',)
        permissions = (('adm_delete_alunoarquivo', 'Pode excluir documento validado da pasta do aluno'),)

    def __str__(self):
        return '{} - {} - {}'.format(self.nome_exibicao, self.data_hora_upload, self.aluno)

    def can_validate(self, user):
        return self.validado is None and user.has_perm('edu.change_alunoarquivo')

    """
    A deleção de documento é permitida se o usuário:
        É o responsável pela validação OU o próprio aluno
        OU o documento ainda não foi validado E não está em um diploma digital emitido E tem permissões de deleção
    """

    def can_delete(self, user=None):
        if user is None:
            user = tl.get_user()
        return self.responsavel_validacao == user or self.aluno.get_user() == user or (self.validado is None or self.validado is False) and self.em_diploma is False and (user.has_perm('edu.delete_alunoarquivo') or user.has_perm('edu.adm_delete_alunoarquivo'))

    def get_tipo_diploma_exibicao(self):
        tipo = TipoAlunoArquivo.OUTROS
        if self.tipo.nome == TipoAlunoArquivo.IDENTIDADE:
            tipo = 'DocumentoIdentidadeDoAluno'
        elif self.tipo.nome == TipoAlunoArquivo.HISTORICO:
            tipo = 'HistoricoEscolar'
        elif self.tipo.nome == TipoAlunoArquivo.CERTIDAO_NASCIMENTO:
            tipo = 'CertidaoNascimento'
        elif self.tipo.nome == TipoAlunoArquivo.CERTIDAO_CASAMENTO:
            tipo = 'CertidaoCasamento'
        elif self.tipo.nome == TipoAlunoArquivo.TITULO_ELEITOR:
            tipo = 'TituloEleitor'
        return tipo

    # TODO: Testar e rever. Creio que dá pra abstrair e jogar pra classe pai!
    @classmethod
    def update_or_create_from_file_bytes(
        cls,
        bytes,
        tipo_conteudo,
        data_hora_upload,
        nome_original,
        nome_exibicao,
        descricao,
        aluno,
        observacao,
        tamanho_em_bytes_para_validar=None,
        hash_sha512_para_validar=None,
        aluno_arquivo_id=None,
    ):
        if aluno_arquivo_id:
            aluno_arquivo = Aluno.objects.filter(pk=aluno_arquivo_id)
            if not aluno_arquivo.exists():
                raise ValidationError('A arquivo do aluno não existe, portanto não pode ser atualizado.')
            aluno_arquivo = aluno_arquivo.first()
            aluno_arquivo_created = False
        else:
            aluno_arquivo = Aluno()
            aluno_arquivo_created = True

        arquivo_unico_created = False
        arquivo_unico = None

        try:
            with transaction.atomic():
                arquivo_unico, arquivo_unico_created = ArquivoUnico.get_or_create_from_file_bytes(
                    bytes=bytes,
                    tipo_conteudo=tipo_conteudo,
                    nome_original_primeiro_upload=nome_original,
                    data_hora_primeiro_upload=data_hora_upload,
                    tamanho_em_bytes_para_validar=tamanho_em_bytes_para_validar,
                    hash_sha512_para_validar=hash_sha512_para_validar,
                )

                # Setando os atributos da Aluno.
                aluno_arquivo.arquivo_unico = arquivo_unico
                aluno_arquivo.nome_original = nome_original
                aluno_arquivo.nome_exibicao = nome_exibicao
                aluno_arquivo.add_extensao_ao_nome_exibicao_com_base_no_nome_original()
                aluno_arquivo.descricao = descricao
                aluno_arquivo.data_hora_upload = data_hora_upload
                aluno_arquivo.solicitacao_etapa = aluno
                aluno_arquivo.observacao = observacao
                aluno_arquivo.save()

                return aluno_arquivo, aluno_arquivo_created, arquivo_unico, arquivo_unico_created
        except Exception as e:
            if arquivo_unico_created:
                arquivo_unico.conteudo.delete(save=False)
            raise e

    def to_pdfa(self):
        file_path = self.arquivo_unico.conteudo.path
        filename, file_extension = os.path.splitext(self.arquivo_unico.conteudo.path)
        jpeg_file_path = tempfile.mktemp(suffix='.jpeg')
        pdf_file_path = tempfile.mktemp(suffix='.pdf')
        viewjpeg_path = '/usr/share/ghostscript/9.53.3/lib/viewjpeg.ps'  # TODO
        if file_extension == '.pdf':
            command = 'gs -q -dPDFA=2 -dBATCH -dNOPAUSE -sDEVICE=pdfwrite -dPDFACompatibilityPolicy=1 -dUseCIEColor -sOutputFile={} {}'.format(pdf_file_path, self.arquivo_unico.conteudo.path)
        else:
            if file_extension == '.jpeg':
                pass
            elif file_extension == '.png' or file_extension == '.jpg':
                command = 'convert {} {}'.format(file_path, jpeg_file_path)
                os.system(command)
            else:
                raise Exception('Não é possível converter esse tipo de arquivo.')
            command = 'gs -q -dPDFA=2  -dBATCH -dNOPAUSE -dNOSAFER -sPAPERSIZE=letter -dPDFACompatibilityPolicy=1 -dUseCIEColor -sDEVICE=pdfwrite -sOutputFile={} {} {}'.format(pdf_file_path, viewjpeg_path, '-c ({}) viewJPEG showpage'.format(jpeg_file_path))
        os.system(command)
        return pdf_file_path
