import datetime
import io

import django
import os
import uuid
import qrcode
import tempfile
import requests
from django.core.files.storage import default_storage
from django.db.models.aggregates import Sum
from comum import signer
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.transaction import atomic
from django.utils import html
from comum.models import RegistroEmissaoDocumento, Configuracao, Vinculo, CertificadoDigital
from comum.utils import libreoffice_new_line, gerar_documento_impressao, somar_data, get_sigla_reitoria
from djtools.db import models
from djtools.storages import cache_file
from djtools.utils import send_mail
from rh.models import Servidor, Funcionario, UnidadeOrganizacional
from djtools.templatetags.filters import format_, normalizar
from edu.managers import FiltroUnidadeOrganizacionalManager
from edu.models.cadastros_gerais import Modalidade, ConfiguracaoLivro, ModeloDocumento, NivelEnsino
from edu.models.cursos import ComponenteCurricular, MatrizCurso
from edu.models.diretorias import CoordenadorRegistroAcademico
from edu.models.logs import LogModel
from edu.models.historico import MatriculaDiario, MatriculaDiarioResumida, AproveitamentoEstudo, CertificacaoConhecimento


class RegistroEmissaoDiploma(LogModel):
    SEARCH_FIELDS = ['aluno__pessoa_fisica__nome_registro', 'aluno__pessoa_fisica__nome_social', 'aluno__matricula']
    AGUARDANDO_REGISTRO = 0
    AGUARDANDO_CORRECAO_DADOS = 1
    AGUARDANDO_CORRECAO_DADOS_DIPLOMA = 11
    AGUARDANDO_ASSINATURA_DOCUMENTACAO = 2
    AGUARDANDO_CORRECAO_HISTORICO = 12
    AGUARDANDO_ASSINATURA_HISTORICO = 13
    AGUARDANDO_ASSINATURA_DIPLOMA = 3
    AGUARDANDO_CONFECCAO_DIPLOMA = 4
    AGUARDANDO_GERACAO_IMPRESSAO = 96
    AGUARDANDO_SINCRONIZACAO = 97
    AGUARDANDO_ASSINATURA_FISICA = 98
    CANCELADO = 99
    FINALIZADO = 100
    SITUACAO_CHOICES = [
        [AGUARDANDO_REGISTRO, 'Aguardando registro'],
        [AGUARDANDO_GERACAO_IMPRESSAO, 'Aguardando geração ou impressão'],
        [AGUARDANDO_SINCRONIZACAO, 'Aguardando início do processo de assinatura digital'],
        [AGUARDANDO_CORRECAO_DADOS, 'Aguardando correção de dados da documentação'],
        [AGUARDANDO_CORRECAO_DADOS_DIPLOMA, 'Aguardando correção de dados do diploma'],
        [AGUARDANDO_ASSINATURA_DOCUMENTACAO, 'Aguardando assinatura da documentação'],
        [AGUARDANDO_CORRECAO_HISTORICO, 'Aguardando correção do histórico'],
        [AGUARDANDO_ASSINATURA_HISTORICO, 'Aguardando assinatura do histórico'],
        [AGUARDANDO_ASSINATURA_DIPLOMA, 'Aguardando assinatura digital do diploma'],
        [AGUARDANDO_CONFECCAO_DIPLOMA, 'Aguardando geração da representação visual do diploma'],
        [AGUARDANDO_ASSINATURA_FISICA, 'Aguardando assinatura física do diploma'],
        [CANCELADO, 'Cancelado'],
        [FINALIZADO, 'Finalizado'],
    ]

    sistema = models.CharFieldPlus(verbose_name='Sistema', default='SUAP', choices=[['SUAP', 'SUAP'], ['Q-ACADÊMICO', 'Q-ACADÊMICO'], ['SICA', 'SICA']])

    aluno = models.ForeignKeyPlus('edu.Aluno')
    livro = models.PositiveIntegerField(null=True)
    folha = models.PositiveIntegerField(null=True)
    numero_registro = models.PositiveIntegerField(verbose_name='Número do Registro', null=True)
    numero_formulario = models.CharFieldPlus(verbose_name='Número do Formulário', null=True, blank=True)
    # processo = models.ForeignKeyPlus('protocolo.Processo', null=True)
    data_registro = models.DateFieldPlus(verbose_name='Data do Registro', null=True, blank=True)
    data_expedicao = models.DateFieldPlus(verbose_name='Data de Expedição', null=True, blank=True)
    pasta = models.CharFieldPlus(null=True, blank=True)
    emissor = models.CurrentUserField()
    via = models.IntegerField()
    cancelado = models.BooleanField(default=False)
    motivo_cancelamento = models.TextField('Motivo do Cancelamento', null=True, blank=False)
    data_cancelamento = models.DateTimeFieldPlus('Data do Cancelamento', null=True, auto_now_add=True)
    codigo_qacademico = models.IntegerField(verbose_name='Código Q-Acadêmico', null=True, blank=True)
    observacao = models.TextField(verbose_name='Observação', null=True, blank=True)

    autenticacao_sistec = models.CharFieldPlus(
        verbose_name='Autenticação SISTEC', null=True, blank=True, help_text='Código de autenticação SISTEC. Obrigatório para alunos de cursos técnicos.'
    )

    configuracao_livro = models.ForeignKey(ConfiguracaoLivro, verbose_name='Configuração de Livro', null=True, on_delete=django.db.models.deletion.CASCADE)

    matriz = models.CharFieldPlus(verbose_name='Matriz', null=True, blank=True)
    autorizacao = models.TextField(verbose_name='Autorização', null=True, blank=True)
    reconhecimento = models.TextField(verbose_name='Reconhecimento', null=True, blank=True)

    ch_geral = models.IntegerField(verbose_name='Carga-Horária Geral', null=True, blank=True)
    ch_especial = models.IntegerField(verbose_name='Carga-Horária Especial', null=True, blank=True)
    ch_estagio = models.IntegerField(verbose_name='Carga-Horária Estágio', null=True, blank=True)
    ch_total = models.IntegerField(verbose_name='Carga-Horária Total', null=True, blank=True)

    empresa_estagio = models.TextField(verbose_name='Empresa do Estágio', null=True, blank=True)

    dirigente_maximo = models.ForeignKeyPlus('rh.PessoaFisica', verbose_name='Dirigente Máximo', null=True, blank=True, related_name='red1_set')
    responsavel_emissao = models.ForeignKeyPlus('rh.PessoaFisica', verbose_name='Responsável pela Emissão', null=True, blank=True, related_name='red2_set')
    responsavel_registro = models.ForeignKeyPlus('rh.PessoaFisica', verbose_name='Responsável pelo Registro', null=True, blank=True, related_name='red3_set')

    data_publicacao_dou = models.DateFieldPlus(verbose_name='Data de Publicação no DOU', null=True, blank=True)
    url_publicacao_dou = models.URLField(verbose_name='URL da Publicação no DOU', null=True, blank=True)

    situacao = models.IntegerField(verbose_name='Situação', null=True, choices=SITUACAO_CHOICES)

    objects = models.Manager()
    locals = FiltroUnidadeOrganizacionalManager('aluno__curso_campus__diretoria__setor__uo')

    class Meta:
        verbose_name = 'Emissão de Diploma/Certificado'
        verbose_name_plural = 'Emissão de Diplomas/Certificados'

    def get_livro(self):
        origem = self.configuracao_livro and self.configuracao_livro.codigo_qacademico and 'Q-Acadêmico' or 'SUAP'
        return (
            self.livro
            and '{} {} ({} / {})'.format(
                self.livro, origem, self.configuracao_livro and self.configuracao_livro.descricao, self.configuracao_livro and self.configuracao_livro.uo.sigla
            )
            or None
        )

    def get_cpf(self):
        return self.aluno.pessoa_fisica.cpf and self.aluno.pessoa_fisica.cpf[4:11] or ''

    def get_emec_curso(self):
        if self.aluno.curso_campus.codigo_emec:
            return f"{self.aluno.curso_campus.codigo_emec} - {self.aluno.curso_campus.descricao_historico}"
        return self.aluno.curso_campus.descricao_historico

    def get_emec_expeditora(self):
        return "{} - {}".format(1082, 'Instituto Federal de Educação, Ciência e Tecnologia do Rio Grande do Norte')

    def get_emec_registradora(self):
        return self.get_emec_expeditora()

    def get_ingresso(self):
        return f"{self.aluno.ano_letivo}/{self.aluno.periodo_letivo}"

    def get_absolute_url(self):
        return f"/edu/registroemissaodiploma/{self.pk:d}/"

    def __str__(self):
        return f'{self.via}ª Via'

    def eh_ultima_via(self):
        return self.via == RegistroEmissaoDiploma.objects.filter(aluno=self.aluno).filter(cancelado=False).values_list('via', flat=True).order_by('-via').first()

    def get_coordenador_registro_academico(self):
        qs = CoordenadorRegistroAcademico.objects.filter(diretoria=self.aluno.curso_campus.diretoria)
        return qs.exists() and qs[0] or None

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        ultimo_registro = RegistroEmissaoDiploma.objects.filter(cancelado=False, aluno=self.aluno).order_by('-id')
        if ultimo_registro:
            self.aluno.data_expedicao_diploma = ultimo_registro[0].data_expedicao
        else:
            self.aluno.data_expedicao_diploma = None
        self.aluno.save()

    def is_assinado_eletronicamente(self):
        qs = self.assinaturaeletronica_set
        return qs.exists() and not qs.filter(data_assinatura__isnull=True).exists()

    def is_assinado_digitalmente(self):
        return self.assinaturadigital_set.exists()

    def get_status_situacao(self):
        descricao = self.get_situacao_display()
        if descricao is None or descricao == 'Finalizado':
            return 'success'
        elif descricao == 'Cancelado':
            return 'error'
        else:
            return 'alert'

    @atomic()
    def cancelar(self):
        if self.eh_ultima_via():
            self.cancelado = True
            self.situacao = RegistroEmissaoDiploma.CANCELADO
            self.save()
            if self.is_eletronico() or self.is_digital():
                if self.is_assinado_eletronicamente():
                    self.assinaturaeletronica_set.first().revogar(self.motivo_cancelamento)
                elif self.is_assinado_digitalmente():
                    self.assinaturadigital_set.first().revogar(self.motivo_cancelamento)
                else:
                    RegistroEmissaoDocumento.objects.filter(tipo='Diploma/Certificado', modelo_pk=self.pk).delete()
                    RegistroEmissaoDocumento.objects.filter(tipo='Histórico Final', modelo_pk=self.aluno.pk).delete()
                    AssinaturaEletronica.objects.filter(registro_emissao_diploma_id=self.pk).delete()
        else:
            raise ValidationError('Apenas a última via pode ser cancelada.')

    @atomic()
    def registrar(self):
        ultima_via = RegistroEmissaoDiploma.objects.exclude(pk=self.pk).filter(aluno=self.aluno).filter(cancelado=False).order_by('-via').first()
        # segunda via de diplomas físicos possuem o mesmo número de livro, folha e registro
        if ultima_via and not self.is_eletronico() and not self.is_digital():
            self.livro = ultima_via.livro
            self.folha = ultima_via.folha
            self.numero_registro = ultima_via.numero_registro
            self.data_registro = ultima_via.data_registro
            self.configuracao_livro = ultima_via.configuracao_livro
        else:
            if self.aluno.is_sica() and not self.is_eletronico() and not self.is_digital():
                configuracao_livro = ConfiguracaoLivro.objects.get(descricao='SICA')
            elif self.aluno.is_qacademico() and not self.is_eletronico() and not self.is_digital():
                configuracao_livro = ConfiguracaoLivro.objects.get(uo=self.aluno.curso_campus.diretoria.setor.uo, codigo_qacademico__isnull=False)
            else:
                # assinatura eletrônica
                if self.requer_assinatura_eletronica_digital():
                    configuracao_livro = ConfiguracaoLivro.objects.filter(
                        descricao=ConfiguracaoLivro.NOME_LIVRO_ELETRONICO
                    ).first()
                    # criar o livro eletrônico caso não exista
                    if configuracao_livro is None:
                        configuracao_livro = ConfiguracaoLivro.objects.create(
                            descricao=ConfiguracaoLivro.NOME_LIVRO_ELETRONICO,
                            uo=UnidadeOrganizacional.objects.suap().get(sigla=get_sigla_reitoria()),
                            numero_livro=1,
                            folhas_por_livro=100000000,
                            numero_folha=1,
                            numero_registro=1,
                        )
                    # adicionar a modalidade do curso ao livro caso não tenha sido adicionada ainda
                    if configuracao_livro.modalidades.filter(pk=self.aluno.curso_campus.modalidade_id).first() is None:
                        configuracao_livro.modalidades.add(
                            self.aluno.curso_campus.modalidade
                        )
                else:  # assinatura manual
                    configuracao_livro = ConfiguracaoLivro.objects.get(uo=self.aluno.curso_campus.diretoria.setor.uo, modalidades=self.aluno.curso_campus.modalidade)
            self.livro = configuracao_livro.numero_livro
            self.folha = configuracao_livro.numero_folha
            self.numero_registro = configuracao_livro.numero_registro
            self.data_registro = datetime.date.today()
            self.configuracao_livro = configuracao_livro
            configuracao_livro.gerar_proximo_numero()
        self.situacao = RegistroEmissaoDiploma.AGUARDANDO_GERACAO_IMPRESSAO
        self.save()

    @classmethod
    @atomic()
    def gerar_registro(cls, aluno, processo, numero_formulario, pasta, autenticacao_sistec):
        ultima_via = RegistroEmissaoDiploma.objects.filter(aluno=aluno).filter(cancelado=False).order_by('-via').first()
        ch_especial = ch_estagio = ch_geral = 0
        empresa_estagio = ''
        if aluno.is_sica():
            historico = aluno.historico_set.all().first()
            ultima_via_sica = historico.ultima_via_emitida
            matriz = f'{historico.matriz.codigo} - {historico.matriz.nome}'
            autorizacao = None
            reconhecimento = historico.matriz.reconhecimento
            ch_geral = historico.get_ch_geral()
            ch_especial = historico.get_ch_especial()
            ch_estagio = historico.carga_horaria_estagio
            ch_total = historico.get_ch_cumprida()
        elif aluno.is_qacademico():
            historico = aluno.get_historico_legado()
            matriz = historico['descricao_matriz']
            ch_total = historico['ch_total']
            autorizacao = historico['resolucao_criacao']
            reconhecimento = historico['reconhecimento_texto']
        else:
            ch_total = aluno.matriz.get_carga_horaria_total_prevista()
            matriz_curso = MatrizCurso.objects.get(curso_campus=aluno.curso_campus_id, matriz=aluno.matriz_id)
            matriz = f'{aluno.matriz.pk} - {aluno.matriz.descricao}'
            autorizacao = str(matriz_curso.get_autorizacao())
            if autorizacao is None:
                raise Exception('Autorização do curso não cadastrada.')
            reconhecimento = str(matriz_curso.get_reconhecimento())
            if reconhecimento is None and matriz_curso.curso_campus.modalidade.nivel_ensino_id == NivelEnsino.GRADUACAO:
                raise Exception('Reconhecimento do curso não cadastrado ou com data de validade expirada.')
            estagios = aluno.get_estagios_historico()
            if estagios.exists():
                ch_estagio = estagios.aggregate(ch_total=Sum('ch_final'))['ch_total']
                empresa_estagio = ', '.join(estagios.values_list('empresa__nome', flat=True))

        if ultima_via is None and aluno.is_sica():
            via = ultima_via_sica + 1
        else:
            via = ultima_via and ultima_via.via + 1 or 1
        registro = RegistroEmissaoDiploma()
        registro.sistema = 'SUAP'
        registro.aluno = aluno
        registro.via = via
        registro.numero_formulario = numero_formulario
        registro.processo = processo
        registro.pasta = pasta
        registro.autenticacao_sistec = autenticacao_sistec
        registro.matriz = matriz
        registro.autorizacao = autorizacao
        registro.reconhecimento = reconhecimento
        registro.ch_especial = ch_especial
        registro.ch_estagio = ch_estagio
        registro.empresa_estagio = empresa_estagio
        registro.ch_geral = ch_geral
        registro.ch_total = ch_total
        registro.data_expedicao = datetime.date.today()
        registro.situacao = RegistroEmissaoDiploma.AGUARDANDO_REGISTRO
        if ultima_via:
            registro.registrar()
        else:
            registro.save()
        return registro

    def gerar_diploma(self, reitor, reitor_exercicio, diretor_geral_exercicio, diretor_academico_exercicio, coordenador_registro_escolar, registro, reitor_protempore=False, diretor_geral_protempore=False):
        self.aluno.curso_campus.diretoria.diretor_geral_exercicio = diretor_geral_exercicio
        self.aluno.curso_campus.diretoria.diretor_academico_exercicio = diretor_academico_exercicio
        self.aluno.curso_campus.diretoria.save()

        titulo_aluno = self.aluno.pessoa_fisica.sexo == 'M' and self.aluno.curso_campus.titulo_certificado_masculino or self.aluno.curso_campus.titulo_certificado_feminino
        vocativo_reitor = None

        titulo_reitor = None
        titulo_diretor_geral = None
        titulo_diretor_academico = None
        titulo_coordenador = None

        em_exercicio = ''

        if reitor_exercicio.sexo == 'M':
            titulo_reitor = self.aluno.curso_campus.diretoria.titulo_autoridade_maxima_masculino
            vocativo_reitor = f'O {titulo_reitor.upper()}'
        else:
            titulo_reitor = self.aluno.curso_campus.diretoria.titulo_autoridade_maxima_feminino
            vocativo_reitor = f'A {titulo_reitor.upper()}'

        if reitor_protempore:
            titulo_reitor = f'{titulo_reitor} Pro Tempore'
            vocativo_reitor = f'{vocativo_reitor} PRO TEMPORE'

        if reitor.pk != reitor_exercicio.pk:
            titulo_reitor = f'{titulo_reitor} em Exercício'
            vocativo_reitor = f'{vocativo_reitor} EM EXERCÍCIO'

        if self.aluno.curso_campus.diretoria.diretor_geral_id == diretor_geral_exercicio.id:
            if diretor_geral_exercicio.sexo == 'M':
                titulo_diretor_geral = self.aluno.curso_campus.diretoria.titulo_autoridade_uo_masculino
            else:
                titulo_diretor_geral = self.aluno.curso_campus.diretoria.titulo_autoridade_uo_feminino
        else:
            if diretor_geral_exercicio.sexo == 'M':
                titulo_diretor_geral = f'{self.aluno.curso_campus.diretoria.titulo_autoridade_uo_masculino} em Exercício'
            else:
                titulo_diretor_geral = f'{self.aluno.curso_campus.diretoria.titulo_autoridade_uo_feminino} em Exercício'

        if diretor_geral_protempore:
            titulo_diretor_geral = f'{titulo_diretor_geral} Pro Tempore'

        if self.aluno.curso_campus.diretoria.diretor_academico_id == diretor_academico_exercicio.id:
            if diretor_academico_exercicio.sexo == 'M':
                titulo_diretor_academico = self.aluno.curso_campus.diretoria.titulo_autoridade_diretoria_masculino
            else:
                titulo_diretor_academico = self.aluno.curso_campus.diretoria.titulo_autoridade_diretoria_feminino
        else:
            if diretor_academico_exercicio.sexo == 'M':
                titulo_diretor_academico = f'{self.aluno.curso_campus.diretoria.titulo_autoridade_diretoria_masculino} em Exercício'
            else:
                titulo_diretor_academico = f'{self.aluno.curso_campus.diretoria.titulo_autoridade_diretoria_masculino} em Exercício'

        if self.aluno.curso_campus.coordenador:
            if self.aluno.curso_campus.coordenador.sexo == 'M':
                titulo_coordenador = 'Coordenador Adjunto'
            else:
                titulo_coordenador = 'Coordenadora Adjunta'
        else:
            titulo_coordenador = 'Não Definido'

        projeto_final = self.aluno.get_projeto_final_aprovado()
        meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
        if projeto_final:
            tema_tcc = projeto_final.titulo
            orientador_tcc = normalizar(projeto_final.orientador.vinculo.pessoa.nome)

            titulacao_orientador_tcc = '-'
            try:
                if projeto_final.orientador and projeto_final.orientador.titulacao:
                    titulacao_orientador_tcc = projeto_final.orientador.titulacao
                elif projeto_final.orientador and projeto_final.orientador.vinculo.eh_servidor():
                    titulacao_orientador_tcc = projeto_final.orientador.vinculo.relacionamento.get_titulacao()
            except Exception:
                pass

            ch_tcc = self.aluno.matriz.ch_componentes_tcc
            nota_tcc = projeto_final.nota or '-'
            dia_tcc = '{}'.format(projeto_final.data_defesa and projeto_final.data_defesa.day or '-')
            mes_tcc = '{}'.format(projeto_final.data_defesa and meses[projeto_final.data_defesa.month - 1] or '-')
            ano_tcc = '{}'.format(projeto_final.data_defesa and projeto_final.data_defesa.year or '-')
            tipo_tcc = projeto_final.tipo
        else:
            tema_tcc = ''
            orientador_tcc = ''
            titulacao_orientador_tcc = ''
            ch_tcc = ''
            nota_tcc = ''
            dia_tcc = ''
            mes_tcc = ''
            ano_tcc = ''
            tipo_tcc = ''

        lista_componentes = []
        lista_professores = []
        lista_titulacao = []
        lista_ch = []
        lista_notas = []
        hoje = datetime.date.today()

        # x#
        registros_por_tipo = []
        situacoes = [MatriculaDiario.SITUACAO_APROVADO, MatriculaDiario.SITUACAO_APROVEITAMENTO_ESTUDO, MatriculaDiario.SITUACAO_CERTIFICACAO_CONHECIMENTO]
        registros_por_tipo.append(
            MatriculaDiario.objects.filter(matricula_periodo__aluno=self.aluno, situacao__in=situacoes).exclude(
                diario__componente_curricular__tipo=ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO
            )
        )
        registros_por_tipo.append(MatriculaDiarioResumida.objects.filter(matricula_periodo__aluno=self.aluno, situacao__in=situacoes))
        for registros_historico in registros_por_tipo:
            for registro_historico in registros_historico:
                nome_professores = registro_historico.get_nomes_professores(excluir_tutores=True).split(', ')
                titulacoes_professores = registro_historico.get_titulacoes_professores(excluir_tutores=True).split(', ')
                descricao_componente = registro_historico.get_descricao_componente()
                mfd = registro_historico.get_media_final_disciplina()
                cht = registro_historico.get_ch_total()
                lista_notas.append('{}'.format(mfd is None and '-' or mfd))
                lista_ch.append('{}'.format(cht is None and '-' or cht))
                lista_componentes.append(descricao_componente)
                if self.aluno.curso_campus.eh_pos_graduacao():
                    for x in nome_professores:
                        lista_professores.append(normalizar(x))
                    for x in titulacoes_professores:
                        lista_titulacao.append(x)
                    for i in range(1, len(nome_professores)):
                        lista_notas.append('.')
                        lista_componentes.append('.')
                        lista_ch.append('.')

        for aproveitamento in AproveitamentoEstudo.objects.filter(matricula_periodo__aluno=self.aluno):
            lista_notas.append(aproveitamento.nota or '-')
            lista_ch.append(aproveitamento.componente_curricular.componente.ch_hora_aula)
            lista_componentes.append(aproveitamento.componente_curricular.componente.descricao_historico)
            lista_professores.append('-')
            lista_titulacao.append('-')

        for certificacao in CertificacaoConhecimento.objects.filter(matricula_periodo__aluno=self.aluno):
            lista_notas.append(certificacao.nota or '-')
            lista_ch.append(certificacao.componente_curricular.componente.ch_hora_aula)
            lista_componentes.append(certificacao.componente_curricular.componente.descricao_historico)
            lista_professores.append('-')
            lista_titulacao.append('-')

        codigo_verificador = registro and (
            'Este documento foi emitido pelo SUAP. Para comprovar sua autenticidade, '
            'acesse {}/comum/autenticar_documento/ - '
            'Código de autenticação: {} - Tipo de Documento: Diploma/Certificado - '
            'Data da emissão: {} '.format(settings.SITE_URL, registro.codigo_verificador[0:7], registro.data_emissao.strftime('%d/%m/%Y'))
        ) or ''

        if self.aluno.curso_campus.modalidade.pk == Modalidade.FIC and self.aluno.matriculaperiodo_set.all()[0].matriculadiario_set.exists():
            calendario_academico = self.aluno.matriculaperiodo_set.all()[0].matriculadiario_set.all()[0].diario.calendario_academico
            data_inicio = calendario_academico.data_inicio
            data_fim = calendario_academico.data_fim

        else:
            data_inicio = self.aluno.data_matricula.date()
            data_fim = self.aluno.dt_conclusao_curso

        if 'sica' in settings.INSTALLED_APPS:
            if not data_fim and self.aluno.historico_set.exists():
                data_fim = self.aluno.dt_conclusao_curso

        nacionalidade = ''
        if self.aluno.nacionalidade:
            if self.aluno.pessoa_fisica.sexo == 'M':
                nacionalidade = self.aluno.nacionalidade.replace('ira', 'iro')
            else:
                nacionalidade = self.aluno.nacionalidade.replace('ido', 'ida')

        ano_conclusao_fic = ''
        if self.aluno.ano_conclusao:
            ano_conclusao_fic = self.aluno.ano_conclusao
        elif self.aluno.dt_conclusao_curso:
            ano_conclusao_fic = self.aluno.dt_conclusao_curso.year

        credenciamento = Configuracao.get_valor_por_chave('edu', 'credenciamento')
        recredenciamento = Configuracao.get_valor_por_chave('edu', 'recredenciamento')

        # se o aluno for do Q-Acadêmico e não tiver sido migrado para o SUAP
        if self.aluno.codigo_academico and not self.aluno.matriz and self.aluno.curso_campus.modalidade.id == Modalidade.ESPECIALIZACAO:
            from edu.q_academico import DAO

            historico_legado = DAO().importar_historico_legado_resumo(self.aluno)
            ch_tcc = int(historico_legado[0].get('ch_projeto_prevista', 0))
            nota_tcc = format_(historico_legado[0].get('projeto_nota'))
            data_tcc_str = historico_legado[0].get('projeto_data_defesa')
            data_tcc = None
            if data_tcc_str:
                data_tcc = datetime.datetime.strptime(data_tcc_str, '%d/%m/%Y')
            dia_tcc = '{}'.format(data_tcc and data_tcc.day or '-')
            mes_tcc = '{}'.format(data_tcc and meses[data_tcc.month - 1] or '-')
            ano_tcc = '{}'.format(data_tcc and data_tcc.year or '-')
            tipo_tcc = historico_legado[0].get('projeto_tipo')
            tema_tcc = historico_legado[0].get('projeto_titulo')
            orientador_tcc = historico_legado[0].get('projeto_orientador')
            titulacao_orientador_tcc = historico_legado[0].get('projeto_titulacao_orientador')
            for linha_historico in historico_legado[1:]:
                lista_notas.append(format_(linha_historico['nota']))
                lista_ch.append(linha_historico['carga_horaria'])
                lista_componentes.append(normalizar(linha_historico['descricao']))
                lista_professores.append(normalizar(linha_historico['nome_professor'] or '-'))
                lista_titulacao.append(linha_historico['titulacao_professor'] or '-')

        dicionario = {
            '#CHGERAL#': self.ch_geral,
            '#CHESPECIAL#': self.ch_especial,
            '#CHESTAGIO#': self.ch_estagio,
            '#EMPRESAESTAGIO#': self.empresa_estagio,
            '#LEI#': 'Criado pela Lei nº 11.892/2008',
            '#NOMECAMPUS#': normalizar(self.aluno.curso_campus.diretoria.setor.uo.nome).replace('Campus', ''),
            '#ALUNO#': normalizar(self.aluno.get_nome_social_composto()),
            '#CREDENCIAMENTO#': credenciamento,
            '#RECREDENCIAMENTO#': recredenciamento,
            '#COLACAO#': format_(self.aluno.get_data_colacao_grau()),
            '#NACIONALIDADE#': nacionalidade.lower(),
            '#NATURALIDADE#': self.aluno.naturalidade,
            '#DATANASCIMENTO#': self.aluno.pessoa_fisica.nascimento_data
            and '{} de {} de {}'.format(
                self.aluno.pessoa_fisica.nascimento_data.day, meses[self.aluno.pessoa_fisica.nascimento_data.month - 1], self.aluno.pessoa_fisica.nascimento_data.year
            )
            or '-',
            '#CPF#': self.aluno.pessoa_fisica.cpf,
            '#PASSAPORTE#': self.aluno.passaporte and f', Passaporte {self.aluno.passaporte}' or '',
            '#RG#': self.aluno.numero_rg,
            '#UFRG#': self.aluno.uf_emissao_rg and self.aluno.uf_emissao_rg.get_sigla() or '',
            '#EMISSORRG#': self.aluno.orgao_emissao_rg,
            '#DATARG#': format_(self.aluno.data_emissao_rg),
            '#CURSO#': self.aluno.curso_campus.descricao_historico,
            '#HABILITACAOPEDAGOGICA#': self.aluno.habilitacao_pedagogica or '',
            '#AREACONCENTRACAO#': self.aluno.curso_campus.area_concentracao or '',
            '#PROGRAMA#': self.aluno.curso_campus.programa or '',
            '#INICIO#': format_(data_inicio),
            '#FIM#': format_(data_fim),
            '#TITULO#': titulo_aluno and titulo_aluno.upper() or '',
            '#CHTOTAL#': self.ch_total,
            '#CIDADE#': normalizar(self.aluno.curso_campus.diretoria.setor.uo.municipio.nome),
            '#UF#': self.aluno.curso_campus.diretoria.setor.uo.municipio.uf,
            '#DATA#': f'{hoje.day} de {meses[hoje.month - 1]} de {hoje.year}',
            '#COORDENADOR#': self.aluno.curso_campus.coordenador and self.aluno.curso_campus.coordenador.nome or '',
            '#AREA#': self.aluno.curso_campus.area or self.aluno.curso_campus.area_capes or '',
            '#TITULOCOORDENADOR#': titulo_coordenador,
            '#OREITOR#': vocativo_reitor,
            '#REITOR#': reitor_exercicio.nome,
            '#TITULOREITOR#': titulo_reitor,
            '#EMEXERCICIO#': em_exercicio,
            '#DIRETORGERAL#': diretor_geral_exercicio.nome,
            '#TITULODIRETORGERAL#': titulo_diretor_geral,
            '#DIRETORACADEMICO#': diretor_academico_exercicio.nome,
            '#TITULODIRETORACADEMICO#': titulo_diretor_academico,
            '#DISCIPLINAS#': libreoffice_new_line(lista_componentes or '-'),
            '#PROFESSORES#': libreoffice_new_line(lista_professores or '-'),
            '#TITULACOES#': libreoffice_new_line(lista_titulacao or '-'),
            '#NOTAS#': libreoffice_new_line(lista_notas or '-', True),
            '#CH#': libreoffice_new_line(lista_ch or '-', True),
            '#REGISTRO#': self.numero_registro,
            '#LIVRO#': self.get_livro(),
            '#FOLHA#': self.folha,
            '#DATAEXPEDICAO#': format_(self.data_expedicao),
            '#PROCESSO#': self.processo and self.processo.numero_processo or self.observacao,
            '#CODIGOVERIFICADOR#': codigo_verificador,
            '#NASCIDO#': self.aluno.pessoa_fisica.sexo == 'M' and 'nascido' or 'nascida',
            '#PORTADOR#': self.aluno.pessoa_fisica.sexo == 'M' and 'portador' or 'portadora',
            '#DIPLOMADO#': self.aluno.pessoa_fisica.sexo == 'M' and 'Diplomado' or 'Diplomada',
            '#AUTORIZACAO#': self.autorizacao,
            '#RECONHECIMENTO#': self.reconhecimento,
            '#DIATCC#': dia_tcc,
            '#MESTCC#': mes_tcc,
            '#ANOTCC#': ano_tcc,
            '#TIPOTCC#': tipo_tcc,
            '#TEMATCC#': html.escape(tema_tcc),
            '#ORIENTADOR#': orientador_tcc,
            '#TITULACAOORIENTADOR#': titulacao_orientador_tcc,
            '#CHTCC#': ch_tcc,
            '#NOTATCC#': nota_tcc,
            '#VIA#': f'{self.via or 1}ª Via',
            '#SERVIDORREGISTROESCOLAR#': coordenador_registro_escolar and coordenador_registro_escolar.servidor.nome or '',
            '#PORTARIAREGISTROESCOLAR#': coordenador_registro_escolar and coordenador_registro_escolar.numero_portaria or '',
            '#NOMEPAI#': normalizar(self.aluno.nome_pai) or '',
            '#NOMEMAE#': normalizar(self.aluno.nome_mae),
            '#ANOCONCLUSAOFIC#': ano_conclusao_fic,
            '#AUTENTICACAOSISTEC#': self.autenticacao_sistec,
            '#HABILITACAO#': f'com habilitação em {self.aluno.habilitacao.descricao},' if self.aluno.habilitacao else ''
            and 'Código Autenticador nº {} atribuído pelo Sistema Nacional de Informações da Educação Profissional e Tecnológica (SISTEC), conforme o Art. 38 da Resolução CNE/CEB n.º 06/2012'.format(
                self.autenticacao_sistec
            )
            or '',
        }

        if coordenador_registro_escolar and coordenador_registro_escolar.eh_coordenador_registro:
            dicionario.update(
                {
                    '#COORDENADORREGISTROESCOLAR#': coordenador_registro_escolar
                    and coordenador_registro_escolar.servidor.sexo == 'M'
                    and 'Coordenador de Registros Acadêmicos'
                    or 'Coordenadora de Registros Acadêmicos'
                }
            )
        else:
            dicionario.update({'#COORDENADORREGISTROESCOLAR#': 'Responsável pela Emissão do Diploma'})

        return dicionario

    def requer_assinatura_eletronica_digital(self):
        return self.is_eletronico() or self.is_digital()

    def is_registro_em_livro_eletronico(self):
        config_livro = self.configuracao_livro
        return config_livro and config_livro.uo.tipo.id == UnidadeOrganizacional.TIPO_REITORIA and config_livro.descricao == ConfiguracaoLivro.NOME_LIVRO_ELETRONICO

    def possui_assinatura_eletronica_digital(self):
        if self.is_eletronico():
            return self.assinaturaeletronica_set.exists()
        if self.is_digital():
            return self.assinaturadigital_set.exists()
        return False

    def possui_assinatura_pendente(self):
        if self.is_eletronico():
            return self.assinaturaeletronica_set.filter(data_assinatura__isnull=True).exists()
        if self.is_digital():
            return not self.assinaturadigital_set.filter(concluida=True).exists()
        return False

    def get_assinatura_eletronica(self):
        return self.assinaturaeletronica_set.first()

    def get_assinatura_digital(self):
        return self.assinaturadigital_set.first()

    def is_eletronico(self):
        return self.aluno.curso_campus.assinatura_eletronica

    def is_digital(self):
        return self.aluno.curso_campus.assinatura_digital

    def enviar_por_email(self):
        obj = self.assinaturaeletronica_set.first()
        if obj:
            obj.enviar_por_email()
        else:
            obj = self.assinaturadigital_set.first()
            if obj:
                obj.enviar_por_email()


class AssinaturaEletronica(LogModel):
    reitor = models.ForeignKeyPlus(Servidor, verbose_name='Reitor', null=True, related_name='assinaturas_reitor')
    reitor_protempore = models.BooleanField(verbose_name='Reitor Pro tempore?', null=True, default=False)
    diretor_geral = models.ForeignKeyPlus(Funcionario, verbose_name='Diretor Geral', null=True)
    diretor_geral_protempore = models.BooleanField(verbose_name='Diretor Geral Pro tempore?', blank=True, default=False)
    diretor_academico = models.ForeignKeyPlus(Funcionario, verbose_name='Diretor Acadêmico', null=True, related_name='assinaturas_diretoracademico')
    diretor_ensino = models.ForeignKeyPlus(Funcionario, verbose_name='Diretor de Ensino', null=True, related_name='assinaturas_diretorensino')
    coordenador_registro_academico = models.ForeignKeyPlus(CoordenadorRegistroAcademico, verbose_name='Coordenador de Registro Acadêmico', null=True)
    modelo_documento = models.ForeignKeyPlus(ModeloDocumento, verbose_name='Modelo de Documento', null=True)

    registro_emissao_diploma = models.ForeignKeyPlus(
        RegistroEmissaoDiploma, verbose_name='Registro de Emissão do Diploma'
    )
    registro_emissao_documento_diploma = models.ForeignKeyPlus(
        RegistroEmissaoDocumento, verbose_name='Registro do Documento do Diploma',
        related_name='assinaturas_diploma', null=True
    )
    registro_emissao_documento_historico = models.ForeignKeyPlus(
        RegistroEmissaoDocumento, verbose_name='Registro do Documento do Histórico',
        related_name='assinaturas_historico', null=True
    )
    diploma = models.FileFieldPlus(verbose_name='Diploma', upload_to='diplomas_eletronicos')
    data_assinatura = models.DateTimeFieldPlus(verbose_name='Finalização das Assinaturas', null=True)
    data_revogacao = models.DateTimeFieldPlus(verbose_name='Data da Revogação', null=True)
    motivo_revogacao = models.TextField(verbose_name='Motivo da Revogação', null=True)

    class Meta:
        verbose_name = 'Assinatura Eletrônica'
        verbose_name_plural = 'Assinaturas Eletrônicas'

    def __str__(self):
        return f'Assinatura #{self.pk}'

    def get_matricula(self):
        return self.registro_emissao_diploma.aluno.matricula

    def get_nome_aluno(self):
        return self.registro_emissao_diploma.aluno.pessoa_fisica.nome

    def get_curso_aluno(self):
        return self.registro_emissao_diploma.aluno.curso_campus

    def get_url_registro(self):
        return self.registro_emissao_documento_diploma.documento.url

    def get_url_diploma(self):
        return self.diploma.url

    def get_url_historico(self):
        if self.registro_emissao_documento_historico:
            return self.registro_emissao_documento_historico.documento.url
        else:
            return f'/edu/emitir_historico_final_pdf/{self.registro_emissao_diploma.aluno.pk}/'

    def enviar_por_email(self):
        to = []
        if self.registro_emissao_diploma.aluno.pessoa_fisica.email:
            to.append(self.registro_emissao_diploma.aluno.pessoa_fisica.email)
        if self.registro_emissao_diploma.aluno.pessoa_fisica.email_secundario:
            to.append(self.registro_emissao_diploma.aluno.pessoa_fisica.email_secundario)
        if self.registro_emissao_diploma.aluno.email_academico:
            to.append(self.registro_emissao_diploma.aluno.email_academico)

        subject = 'Emissão de Diploma/Histórico'
        body = '{}, \nseguem os links para dowload do seu diploma e histórico final:\n\n{}/{}\n\n{}/{}'.format(
            self.registro_emissao_diploma.aluno.pessoa_fisica.nome,
            settings.SITE_URL, self.get_url_diploma(),
            settings.SITE_URL, self.get_url_historico()
        )
        from_email = settings.DEFAULT_FROM_EMAIL
        send_mail(subject, body, from_email, to, fail_silently=True)

    def assinar(self, request):
        from edu.views import gerar_autenticacao_diploma_pdf, emitir_historico_final_eletronico_pdf
        vinculo = request.user.get_vinculo()
        registro_emissao_documento_diploma = gerar_autenticacao_diploma_pdf(request, pk=self.registro_emissao_diploma.pk)
        registro_emissao_documento_historico = None
        if self.registro_emissao_diploma.aluno.is_qacademico() or self.registro_emissao_diploma.aluno.is_sica():
            registro_emissao_documento_historico = emitir_historico_final_eletronico_pdf(request, pk=str(self.registro_emissao_diploma.aluno.pk), legado=True)
        elif self.registro_emissao_diploma.aluno.matriz and not self.registro_emissao_diploma.aluno.matriz.estrutura.proitec:
            registro_emissao_documento_historico = emitir_historico_final_eletronico_pdf(request, pk=str(self.registro_emissao_diploma.aluno.pk))
        id_certificado, senha_certificado = request.session['sessao_assinatura_eletronica']

        chave_assinatura = uuid.uuid1().hex
        data_assinatura = datetime.datetime.now()

        if self.registro_emissao_documento_diploma is None:
            if self.solicitacaoassinaturaeletronica_set.count() == 1:
                dados_assinatura = []
                dados_assinatura.append(
                    dict(
                        nome=vinculo.pessoa.nome,
                        matricula=vinculo.relacionamento.matricula,
                        data=data_assinatura.strftime('%d/%m/%Y %H:%M:%S'),
                        chave=chave_assinatura
                    )
                )

            reitoria = UnidadeOrganizacional.objects.suap().get(sigla=get_sigla_reitoria())
            reitor = reitoria.get_diretor_geral(True)[0]
            dicionario = self.registro_emissao_diploma.gerar_diploma(
                reitor,
                self.reitor,
                self.diretor_geral,
                self.diretor_academico or self.diretor_ensino,
                self.coordenador_registro_academico,
                registro_emissao_documento_diploma,
                self.reitor_protempore,
                self.diretor_geral_protempore,
            )
            caminho_arquivo = gerar_documento_impressao(dicionario, io.BytesIO(self.modelo_documento.template.read()))
            if not caminho_arquivo:
                raise Exception('Documento não encontrado.')
            with open(caminho_arquivo, "rb") as local_filename:
                content = local_filename.read()
            caminho_relativo = os.path.join('diplomas_eletronicos', '{}-{}'.format(chave_assinatura, caminho_arquivo.split('/')[-1]))
            default_storage.save(caminho_relativo, io.BytesIO(content))
            os.unlink(caminho_arquivo)

            AssinaturaEletronica.objects.filter(pk=self.pk).update(
                registro_emissao_documento_diploma=registro_emissao_documento_diploma,
                registro_emissao_documento_historico=registro_emissao_documento_historico,
                diploma=caminho_relativo
            )

        # Realizando a assinatura com o certifiado digital A1
        self = AssinaturaEletronica.objects.get(pk=self.pk)

        if vinculo.pessoa.id == self.reitor.id:
            titulo = 'Reitor' if self.reitor.sexo == 'M' else 'Reitora'
            if not self.reitor.eh_reitor():
                titulo = f'{titulo} em Exercício'
            if self.reitor_protempore:
                titulo = f'{titulo} Pro Tempore'
        elif vinculo.pessoa.id == self.diretor_geral.id:
            titulo = 'Diretor Geral' if self.diretor_geral.sexo == 'M' else 'Diretora Geral'
            if self.diretor_geral_id != self.registro_emissao_diploma.aluno.curso_campus.diretoria.diretor_geral_id:
                titulo = f'{titulo} em Exercício'
            if self.diretor_geral_protempore:
                titulo = f'{titulo} Pro Tempore'

        certificado_digital = CertificadoDigital.objects.get(pk=id_certificado)
        if not self.contem_assinatura(vinculo, self.registro_emissao_documento_diploma.documento):
            certificado_digital.assinar_arquivo_pdf(
                self.registro_emissao_documento_diploma.documento.name,
                senha_certificado, adicionar_texto=False, adicionar_imagem=True,
                tipo_documento=self.registro_emissao_documento_diploma.tipo,
                x=50, y=740, bgcolor='#EEEEEE', page=1, titulo=titulo,
                codigo_autenticacao=self.registro_emissao_documento_diploma.codigo_verificador[0:7]
            )
        if self.registro_emissao_documento_historico and not self.contem_assinatura(vinculo, self.registro_emissao_documento_historico.documento):
            certificado_digital.assinar_arquivo_pdf(
                self.registro_emissao_documento_historico.documento.name,
                senha_certificado, adicionar_texto=True, adicionar_imagem=True,
                tipo_documento=self.registro_emissao_documento_diploma.tipo,
                x=50, y=790, bgcolor='#EEEEEE', titulo=titulo,
                codigo_autenticacao=self.registro_emissao_documento_diploma.codigo_verificador[0:7]
            )

        if not self.contem_assinatura(vinculo, self.diploma):
            bgcolor = '#ebf3e5'
            if self.modelo_documento.modalidade_id in (Modalidade.FIC, Modalidade.PROEJA_FIC_FUNDAMENTAL):
                bgcolor = '#f8faf9'
            if self.modelo_documento.modalidade_id in (Modalidade.CONCOMITANTE, Modalidade.SUBSEQUENTE, Modalidade.INTEGRADO, Modalidade.INTEGRADO_EJA):
                bgcolor = '#e7efeb'
            if self.modelo_documento.modalidade_id in (Modalidade.TECNOLOGIA, Modalidade.ENGENHARIA, Modalidade.BACHARELADO, Modalidade.LICENCIATURA):
                bgcolor = '#d8ead9'
            if self.modelo_documento.modalidade_id in (Modalidade.ESPECIALIZACAO, Modalidade.MESTRADO, Modalidade.DOUTORADO, Modalidade.APERFEICOAMENTO):
                bgcolor = '#e0e1dd'
            certificado_digital.assinar_arquivo_pdf(
                self.diploma.name,
                senha_certificado, adicionar_texto=False, adicionar_imagem=True,
                tipo_documento=self.registro_emissao_documento_diploma.tipo,
                x=270, y=470, bgcolor=bgcolor, page=1, titulo=titulo,
                codigo_autenticacao=self.registro_emissao_documento_diploma.codigo_verificador[0:7]
            )

        if self.contem_assinatura(vinculo=vinculo):
            solicitacao_assinatura = self.solicitacaoassinaturaeletronica_set.get(vinculo=vinculo)
            solicitacao_assinatura.data_assinatura = data_assinatura
            solicitacao_assinatura.chave = chave_assinatura
            solicitacao_assinatura.save()

        if not self.solicitacaoassinaturaeletronica_set.filter(data_assinatura__isnull=True).exists() and self.contem_assinatura():
            AssinaturaEletronica.objects.filter(pk=self.pk).update(
                data_assinatura=data_assinatura,
            )
            self.registro_emissao_diploma.enviar_por_email()
            self.registro_emissao_diploma.situacao = RegistroEmissaoDiploma.FINALIZADO
            self.registro_emissao_diploma.save()

    @atomic()
    def revogar(self, motivo):
        self.motivo_revogacao = motivo
        self.data_revogacao = datetime.datetime.now()
        self.save()
        if not self.registro_emissao_diploma.cancelado:
            self.registro_emissao_diploma.cancelado = True
            self.registro_emissao_diploma.data_cancelamento = self.data_revogacao
            self.registro_emissao_diploma.motivo_cancelamento = motivo
            self.registro_emissao_diploma.save()
        self.registro_emissao_documento_diploma.cancelado = True
        self.registro_emissao_documento_diploma.save()
        if self.registro_emissao_documento_historico:
            self.registro_emissao_documento_historico.cancelado = True
            self.registro_emissao_documento_historico.save()

    def contem_assinatura(self, vinculo=None, documento=None):
        cpfs = []
        if vinculo is None:
            for solicitacao_assinatura in self.solicitacaoassinaturaeletronica_set.all():
                cpf = solicitacao_assinatura.vinculo.pessoa.get_cpf_ou_cnpj()
                cpfs.append(cpf.replace('.', '').replace('-', '').replace('/', ''))
        else:
            cpf = vinculo.pessoa.get_cpf_ou_cnpj().replace('.', '').replace('-', '').replace('/', '')

        documentos = []
        if documento is None:
            if self.registro_emissao_diploma.aluno.matriz and not self.registro_emissao_diploma.aluno.matriz.estrutura.proitec:
                if self.registro_emissao_documento_historico is None:
                    return False
                documentos.append(self.registro_emissao_documento_historico.documento)

            if self.registro_emissao_documento_diploma is None or self.diploma is None:
                return False
            documentos.append(self.registro_emissao_documento_diploma.documento)
            documentos.append(self.diploma)
        else:
            documentos.append(documento)

        for documento in documentos:
            if documento and documento.name and documento.name.endswith('.pdf'):
                local_filename = cache_file(documento.name)
                if os.path.exists(local_filename):
                    assinaturas = signer.verify(local_filename)
                    if vinculo is None:
                        if len(cpfs) == len(assinaturas):
                            for cpf in cpfs:
                                if cpf not in ''.join(assinaturas):
                                    return False
                        else:
                            return False
                    else:
                        if cpf not in ''.join(assinaturas):
                            return False
                else:
                    return False
            else:
                return False
        return True


class SolicitacaoAssinaturaEletronica(LogModel):
    assinatura_eletronica = models.ForeignKeyPlus(AssinaturaEletronica, verbose_name='Assinatura Eletrônica')
    vinculo = models.ForeignKeyPlus(Vinculo, verbose_name='Vínculo')
    chave = models.CharFieldPlus(verbose_name='Chave', null=True)
    data_assinatura = models.DateTimeFieldPlus(verbose_name='Data da Assinatura', null=True)

    class Meta:
        verbose_name = 'Solicitação de Assinatura Eletrônica'
        verbose_name_plural = 'Solicitações de Assinatura Eletrônica'


class CodigoAutenticadorSistec(LogModel):
    cpf = models.BrCpfField(verbose_name='CPF')
    codigo_unidade = models.CharFieldPlus(verbose_name='Código da Unidade')
    codigo_curso = models.CharFieldPlus(verbose_name='Código do Curso')
    codigo_autenticacao = models.CharFieldPlus(verbose_name='Código de Autenticação')

    class Meta:
        verbose_name = 'Código Autenticador Sistec'
        verbose_name_plural = 'Códigos Autenticadores Sistec'

    def __str__(self):
        return self.codigo_autenticacao

    def atualizar_registro_emissao_diploma(self):
        return RegistroEmissaoDiploma.objects.filter(
            aluno__curso_campus__codigo_sistec=self.codigo_unidade,
            aluno__curso_campus__diretoria__setor__uo__codigo_sistec=self.codigo_curso,
            aluno__pessoa_fisica__cpf=self.cpf
        ).update(autenticacao_sistec=self.codigo_autenticacao)


class AssinaturaDigital(LogModel):

    SITUACAO_CHOICES = [
        [0, 'Esperando geração'],
        [1, 'Geração iniciada'],
        [2, 'Arquivo Gerado'],
        [3, 'Assinatura em construção'],
        [4, 'Assinatura iniciada'],
        [5, 'Assinatura iniciada'],
        [6, 'Assinatura finalizada'],
        [7, 'Registro iniciado'],
        [8, 'Registrando'],
        [9, 'Registrando'],
        [10, 'Documento Concluído'],
        [11, 'Documento Suspenso'],
        [12, 'Revogação Solicitada'],
        [13, 'Revogando'],
        [14, 'Revogado'],
        [500, 'Erro preparando geração do documento'],
        [501, 'Erro gerando documento;'],
        [502, 'Erro inicializando processamento de assinaturas'],
        [503, 'Erro finalizando processamento de assinaturas'],
        [504, 'Erro Iniciando processo de registro'],
        [505, 'Erro finalizando processo de registro'],
        [506, 'Erro revogando documento']
    ]

    reitor = models.ForeignKeyPlus(Servidor, verbose_name='Reitor', null=True, related_name='assinaturas_digitais_reitor')
    reitor_protempore = models.BooleanField(verbose_name='Reitor Pro tempore?', null=True, default=False)
    diretor_geral = models.ForeignKeyPlus(Funcionario, verbose_name='Diretor Geral', null=True)
    diretor_geral_protempore = models.BooleanField(verbose_name='Diretor Geral Pro tempore?', blank=True, default=False)
    diretor_academico = models.ForeignKeyPlus(Funcionario, verbose_name='Diretor Acadêmico', null=True, related_name='assinaturas_digitais_diretoracademico')
    diretor_ensino = models.ForeignKeyPlus(Funcionario, verbose_name='Diretor de Ensino', null=True, related_name='assinaturas_digitais_diretorensino')
    coordenador_registro_academico = models.ForeignKeyPlus(CoordenadorRegistroAcademico, verbose_name='Coordenador de Registro Acadêmico', null=True)
    modelo_documento = models.ForeignKeyPlus(ModeloDocumento, verbose_name='Modelo de Documento', null=True)
    registro_emissao_diploma = models.ForeignKeyPlus(
        RegistroEmissaoDiploma, verbose_name='Registro de Emissão do Diploma'
    )
    registro_emissao_documento_diploma = models.ForeignKeyPlus(
        RegistroEmissaoDocumento, verbose_name='Registro do Documento do Diploma',
        related_name='assinaturas_digitais_diploma', null=True
    )
    registro_emissao_documento_historico = models.ForeignKeyPlus(
        RegistroEmissaoDocumento, verbose_name='Registro do Documento do Histórico',
        related_name='assinaturas_digitais_historico', null=True
    )
    diploma = models.FileFieldPlus(verbose_name='Diploma', upload_to='diplomas_eletronicos')
    concluida = models.BooleanField(verbose_name='Concluída', default=False)
    data_revogacao = models.DateTimeFieldPlus(verbose_name='Data da Revogação', null=True)
    motivo_revogacao = models.TextField(verbose_name='Motivo da Revogação', null=True)
    id_documentacao_academica_digital = models.IntegerField(
        verbose_name='Identificador da Documentação Acadêmica Digital', default=0
    )
    status_documentacao_academica_digital = models.IntegerField(
        verbose_name='Situação da Documentação Acadêmica Digital', null=True, choices=SITUACAO_CHOICES
    )
    id_dados_diploma_digital = models.IntegerField(
        verbose_name='Identificador dos Dados do Diploma Digital', default=0
    )
    status_historico_escolar = models.IntegerField(
        verbose_name='Situação do Histórico Escolar', null=True, choices=SITUACAO_CHOICES
    )
    id_historico_escolar = models.IntegerField(
        verbose_name='Identificador do Histórico Escolar', default=0
    )
    status_dados_diploma_digital = models.IntegerField(
        verbose_name='Situação dos Dados do Documentação Digital', null=True, choices=SITUACAO_CHOICES
    )
    id_representacao_diploma_digital = models.IntegerField(
        verbose_name='Identificador da Representação do Diploma Digital', default=0
    )
    status_representacao_diploma_digital = models.IntegerField(
        verbose_name='Situação da Representação do Documentação Digital', null=True, choices=SITUACAO_CHOICES
    )

    class Meta:
        verbose_name = 'Assinatura Eletrônica'
        verbose_name_plural = 'Assinaturas Eletrônicas'

    def __str__(self):
        return f'Assinatura #{self.pk}'

    def get_matricula(self):
        return self.registro_emissao_diploma.aluno.matricula

    def get_nome_aluno(self):
        return self.registro_emissao_diploma.aluno.pessoa_fisica.nome

    def get_curso_aluno(self):
        return self.registro_emissao_diploma.aluno.curso_campus

    def get_url_diploma(self):
        if self.concluida:
            return self.get_url_pdf_representacao_visual()
        return self.diploma.url

    def get_url_registro(self):
        return '{}{}'.format(settings.SITE_URL, self.registro_emissao_documento_diploma and self.registro_emissao_documento_diploma.get_url_download_documento() or f'/edu/registroemissaodiploma_pdf/{self.registro_emissao_diploma_id}/?digital=1')

    def get_url_historico(self):
        return '{}{}'.format(settings.SITE_URL, self.registro_emissao_documento_historico and self.registro_emissao_documento_historico.get_url_download_documento() or f'/edu/emitir_historico_final_pdf/{self.registro_emissao_diploma.aluno.pk}/?digital=1')

    def get_url_xml_documentacao_academica(self):
        return f'/edu/baixar_xml_documentacao_academica/{self.pk}/'

    def get_url_xml_historico_escolar(self):
        return f'/edu/baixar_xml_historico_escolar/{self.pk}/'

    def get_url_status_assinaturas(self):
        return f'/edu/consultar_status_assinaturas_digitais/{self.pk}/'

    def get_url_xml_dados_diploma(self):
        return f'/edu/baixar_xml_dados_diploma/{self.pk}/'

    def get_url_pdf_representacao_visual(self):
        return f'/edu/baixar_pdf_representacao_visual/{self.pk}/'

    def gerar_representacao_visual(self):
        chave_assinatura = uuid.uuid1().hex
        reitoria = UnidadeOrganizacional.objects.suap().get(sigla=get_sigla_reitoria())
        reitor = reitoria.get_diretor_geral(True)[0]
        dicionario = self.registro_emissao_diploma.gerar_diploma(
            reitor,
            self.reitor,
            self.diretor_geral,
            self.diretor_academico or self.diretor_ensino,
            self.coordenador_registro_academico,
            None,
            self.reitor_protempore,
            self.diretor_geral_protempore,
        )
        url_xml = f'{settings.SITE_URL}{self.get_url_xml_dados_diploma()}'
        codigo_validacao = requests.get(url_xml).text.split('<CodigoValidacao>')[1].split('</CodigoValidacao>')[0]
        url_validacao = f'{settings.SITE_URL}/edu/diploma_digital/{self.registro_emissao_diploma_id}/{codigo_validacao}/'
        qr_code_path = tempfile.mktemp('.png')
        img = qrcode.make(url_validacao)
        img.save(qr_code_path)
        dicionario['#URLXML#'] = url_xml
        dicionario['#CODIGOVALIDACAO#'] = codigo_validacao
        dicionario['#URLVALIDACAO#'] = url_validacao
        caminho_arquivo = gerar_documento_impressao(dicionario, io.BytesIO(self.modelo_documento.template.read()), pdfa=True, imagem_path=qr_code_path)
        if not caminho_arquivo:
            raise Exception('Documento não encontrado.')
        with open(caminho_arquivo, "rb") as tmp:
            content = tmp.read()
        caminho_relativo = os.path.join('diplomas_eletronicos', '{}-{}'.format(chave_assinatura, caminho_arquivo.split('/')[-1]))
        default_storage.save(caminho_relativo, io.BytesIO(content))
        os.unlink(caminho_arquivo)
        AssinaturaDigital.objects.filter(pk=self.pk).update(diploma=caminho_relativo)
        return AssinaturaDigital.objects.get(pk=self.pk)

    def enviar_por_email(self):
        to = []
        if self.registro_emissao_diploma.aluno.pessoa_fisica.email:
            to.append(self.registro_emissao_diploma.aluno.pessoa_fisica.email)
        if self.registro_emissao_diploma.aluno.pessoa_fisica.email_secundario:
            to.append(self.registro_emissao_diploma.aluno.pessoa_fisica.email_secundario)
        if self.registro_emissao_diploma.aluno.email_academico:
            to.append(self.registro_emissao_diploma.aluno.email_academico)

        subject = 'Emissão de Diploma Digital'
        body = '{}, \nseguem os links para dowload do seu histórico final, diploma digital e de sua representação visual:\n\n{}{}\n\n{}{}\n\n{}{}'.format(
            self.registro_emissao_diploma.aluno.pessoa_fisica.nome, settings.SITE_URL, self.get_url_xml_dados_diploma(), settings.SITE_URL, self.get_url_pdf_representacao_visual(), settings.SITE_URL, self.get_url_historico())
        from_email = settings.DEFAULT_FROM_EMAIL
        send_mail(subject, body, from_email, to, fail_silently=True)

    def baixar_xml_documentacao_academica(self):
        from edu.diploma_digital.rap import AssinadorDigital
        assinador_digital = AssinadorDigital()
        return assinador_digital.baixar_xml(self.id_documentacao_academica_digital, as_http_response=True)

    def baixar_xml_historico_escolar(self):
        from edu.diploma_digital.rap import AssinadorDigital
        assinador_digital = AssinadorDigital()
        return assinador_digital.baixar_xml(self.id_historico_escolar, as_http_response=True)

    def consultar_status_assinaturas(self):
        from edu.diploma_digital.rap import AssinadorDigital
        assinador_digital = AssinadorDigital()
        dados = dict()
        if self.id_documentacao_academica_digital:
            dados['Documentação Acadêmica'] = assinador_digital.consultar_status_documento(
                self.id_documentacao_academica_digital
            )
        if self.id_historico_escolar:
            dados['Histórico Escolar'] = assinador_digital.consultar_status_documento(
                self.id_historico_escolar
            )
        if self.id_dados_diploma_digital:
            dados['Dados do Diploma'] = assinador_digital.consultar_status_documento(
                self.id_dados_diploma_digital
            )
        return dados

    def baixar_xml_dados_diploma(self):
        from edu.diploma_digital.rap import AssinadorDigital
        assinador_digital = AssinadorDigital()
        return assinador_digital.baixar_xml(self.id_dados_diploma_digital, as_http_response=True)

    def baixar_pdf_representacao_visual(self):
        from edu.diploma_digital.rap import AssinadorDigital
        assinador_digital = AssinadorDigital()
        return assinador_digital.baixar_pdf(self.id_representacao_diploma_digital, as_http_response=True)

    def revogar(self, motivo):
        from edu.diploma_digital.rap import AssinadorDigital
        assinador_digital = AssinadorDigital()
        if self.id_documentacao_academica_digital:
            assinador_digital.revogar_documento(
                self.id_documentacao_academica_digital
            )
        if self.id_dados_diploma_digital:
            assinador_digital.revogar_documento(
                self.id_dados_diploma_digital
            )
        if self.id_representacao_diploma_digital:
            assinador_digital.revogar_documento(
                self.id_representacao_diploma_digital
            )
        self.motivo_revogacao = motivo
        self.data_revogacao = datetime.datetime.now()
        self.save()
        self.registro_emissao_diploma.cancelado = True
        self.registro_emissao_diploma.motivo_cancelamento = motivo
        self.registro_emissao_diploma.save()


class SincronizacaoAssinaturaDigital(models.ModelPlus):
    assinatura_digital = models.ForeignKeyPlus(AssinaturaDigital, verbose_name='Registro de Emissão')
    data_hora = models.DateTimeField(verbose_name='Data/Hora', auto_now=True)
    detalhe = models.CharFieldPlus(verbose_name='Detalhe')

    class History:
        disabled = True

    class Meta:
        verbose_name = 'Registro de Sincronização'
        verbose_name_plural = 'Registros de Sincronização'
        ordering = '-data_hora',

    def __str__(self):
        return f'Registro de Sincronização {self.pk}'


class CertificadoDiploma(LogModel):
    aluno = models.ForeignKeyPlus('edu.Aluno', verbose_name='Aluno')
    # processo = models.ForeignKeyPlus('processo_eletronico.Processo', verbose_name='Processo')
    validade = models.DateFieldPlus(verbose_name='Validade')

    class Meta:
        verbose_name = 'Certificado de Conclusão'
        verbose_name_plural = 'Certificados de Conclusão'

    def __str__(self):
        return f'Certificado de Emissão de Diploma #{self.id}'

    def save(self):
        self.validade = somar_data(datetime.date.today(), 120)
        super().save()
