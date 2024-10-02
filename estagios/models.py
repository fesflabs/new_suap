import calendar
import datetime
import hashlib
from decimal import Decimal

import numpy
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.aggregates import Avg, Sum
from django.utils.safestring import mark_safe

from comum.models import Configuracao
from convenios.models import Convenio
from djtools.db import models
from djtools.templatetags.filters import format_, in_group
from djtools.utils import send_mail, send_notification
from edu.models import Aluno, Professor, CursoCampus, Turno, MatriculaDiario, Aula, Falta
from edu.models.cadastros_gerais import Modalidade
from estagios.utils import get_coordenadores_estagio, get_coordenadores_nomes, get_coordenadores_emails, get_situacoes_irregulares, get_coordenadores_vinculos
from rh.models import PessoaJuridica, Pessoa, Servidor


class AtividadeProfissionalEfetiva(models.ModelPlus):
    TIPO_EMPREGO_CARGO_OU_FUNCAO = 1
    TIPO_ATIVIDADE_PROFISSIONAL_AUTONOMA = 2
    TIPO_ATIVIDADE_EMPRESARIAL = 3
    TIPO_PROGRAMA_APRENDIZAGEM_EXTERNO = 4
    TIPO_OUTRO = 5
    TIPO = [
        [TIPO_EMPREGO_CARGO_OU_FUNCAO, 'Emprego, Cargo ou Função'],
        [TIPO_ATIVIDADE_PROFISSIONAL_AUTONOMA, 'Atividade Profissional Autônoma'],
        [TIPO_ATIVIDADE_EMPRESARIAL, 'Atividade Empresarial'],
        [TIPO_PROGRAMA_APRENDIZAGEM_EXTERNO, 'Programa de Aprendizagem Externo'],
        [TIPO_OUTRO, 'Outro(a)'],
    ]

    EM_ANDAMENTO = 1
    CONCLUIDA = 2
    NAO_CONCLUIDA = 3
    SITUACOES = [[EM_ANDAMENTO, 'Em andamento'], [CONCLUIDA, 'Concluída'], [NAO_CONCLUIDA, 'Não concluída']]

    CANCELAMENTO_PEDIDO_ALUNO = 1
    CANCELAMENTO_FIM_VINCULO = 2
    CANCELAMENTO_INSTITUICAO_ENSINO = 3
    OUTRO_MOTIVO = 4
    MOTIVO_CANCELAMENTO_CHOICHES = [
        [CANCELAMENTO_PEDIDO_ALUNO, 'Cancelamento a pedido do(a) aluno(a)'],
        [CANCELAMENTO_FIM_VINCULO, 'Cancelamento motivado por fim de vínculo'],
        [CANCELAMENTO_INSTITUICAO_ENSINO, 'Cancelamento a pedido da Instituição de Ensino'],
        [OUTRO_MOTIVO, 'Outro motivo'],
    ]

    # Dados Gerais
    aluno = models.ForeignKeyPlus(Aluno, verbose_name='Aluno')
    instituicao = models.CharFieldPlus(
        'Instituição de Realização da Atividade', default='', blank=True, null=True, help_text='Em caso de atividade profissional autônoma desnecessário o preenchimento.'
    )
    razao_social = models.CharFieldPlus('Razão Social', blank=True, null=True, help_text='Em caso de profissional liberal, preencher o nome do profissional.')
    orientador = models.ForeignKeyPlus(Professor, verbose_name='Orientador')
    tipo = models.IntegerField('Tipo desta Atividade Profissional Efetiva', choices=TIPO, null=True, blank=False)
    descricao_outro_tipo = models.CharFieldPlus('Descrição de Outro Tipo', null=True, blank=True)

    # Período e Carga Horária
    inicio = models.DateFieldPlus('Data de Início')
    data_prevista_encerramento = models.DateFieldPlus('Data Prevista para Encerramento')
    ch_semanal = models.PositiveSmallIntegerField('Carga Horária Semanal')

    # Documentação
    documentacao_comprobatoria = models.FileFieldPlus(
        'Documentação Comprobatória',
        blank=False,
        null=False,
        max_length=255,
        upload_to='atividade_profissional_efetiva/documentacao_comprobatoria',
        help_text='Documentação que comprove que o aluno realiza atividades '
        'compatíveis com a prática profissional exigida pelo seu '
        'curso (Ex. Cópia da Carteira de Trabalho, do Contrato de '
        'Trabalho, conselho profissional de classe, etc.)',
    )
    plano_atividades = models.FileFieldPlus(
        'Plano de Atividades',
        blank=False,
        null=False,
        max_length=255,
        upload_to='atividade_profissional_efetiva/planos_atividades',
        help_text='Plano de Atividades de acordo com a Resolução 25/2019, modelo disponível no endereço: http://portal.ifrn.edu.br/extensao/estagios-e-egressos',
    )

    # Relação das Atividades
    atividades = models.TextField('Atividades Planejadas', default='')

    # Encerramento
    anterior_20171 = models.BooleanField(
        'Atividade Profissional Efetiva anterior a 2017.1 (30/09/2017)?',
        help_text='Marcar "Sim" caso esta Atividade Profissional Efetiva tenha se encerrado até o dia 30/09/2017.',
        default=None,
        choices=[[None, '-------'], [True, 'Sim'], [False, 'Não']], null=True, blank=True
    )
    encerramento = models.DateFieldPlus('Data de Encerramento', blank=False, null=True)
    ch_final = models.IntegerField('Carga Horária Cumprida', blank=False, null=True)
    relatorio_final_aluno = models.FileFieldPlus(
        'Declaração de Realização de Atividade Profissional Efetiva',
        blank=False,
        null=True,
        max_length=255,
        upload_to='atividade_profissional_efetiva/relatorio_final_aluno',
        help_text='Modelo disponível em: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/atividade-profissional-efetiva',
    )
    observacoes = models.TextField('Observações', default='', blank=True, null=True)

    # Cadastro do Cancelamento
    cancelamento = models.DateFieldPlus(
        'Data do Cancelamento', null=True, blank=False, help_text='Data em que de fato não foi mais possível a realização da atividade profissional efetiva.'
    )
    motivo_cancelamento = models.IntegerField('Motivo do Encerramento', choices=MOTIVO_CANCELAMENTO_CHOICHES, null=True, blank=False)
    descricao_cancelamento = models.TextField('Descrição do Cancelamento', null=True, blank=True)

    situacao = models.IntegerField('Situação', choices=SITUACOES, null=True, blank=False, default=EM_ANDAMENTO)

    # Prazo para regularizar a matrícula
    prazo_final_regularizacao_matricula_irregular = models.DateFieldPlus('Prazo Final para Regularizar a Matrícula', null=True, blank=True)

    # Avaliação da Atividade Profissional Efetiva por parte do Aluno
    AVALICAO_CONCEITO_EXCELENTE = 1
    AVALICAO_CONCEITO_BOM = 2
    AVALICAO_CONCEITO_REGULAR = 3
    AVALICAO_CONCEITO_RUIM = 4
    AVALICAO_CONCEITO_PESSIMO = 5
    AVALICAO_CONCEITO_CHOICES = [
        [AVALICAO_CONCEITO_EXCELENTE, 'Excelente'],
        [AVALICAO_CONCEITO_BOM, 'Bom'],
        [AVALICAO_CONCEITO_REGULAR, 'Regular'],
        [AVALICAO_CONCEITO_RUIM, 'Ruim'],
        [AVALICAO_CONCEITO_PESSIMO, 'Péssimo'],
    ]

    REALIZADA_SIM = 1
    REALIZADA_NAO = 2
    PARCIALMENTE_REALIZADA = 3
    REALIZADA_CHOICES = [[REALIZADA_SIM, 'Realizadas'], [REALIZADA_NAO, 'Não Realizadas'], [PARCIALMENTE_REALIZADA, 'Parcialmente Realizadas']]

    # Atividades Previstas
    avaliacao_atividades = models.IntegerField('Sobre as Atividades', choices=REALIZADA_CHOICES, null=True, blank=False)

    # Desenvolvimento das atividades
    comentarios_atividades = models.TextField(
        'Comentários sobre o desenvolvimento das atividades',
        null=True,
        blank=True,
        help_text='Descreva atividades que foram realizadas parcialmente ou que não foram realizadas e justifique.',
    )

    # Atividades não-previstas
    outras_atividades = models.TextField('Realizou atividades não previstas no plano de atividades? Informe e justifique', blank=True, null=True)

    # relação teoria/prática (somente relatório do aprendiz)
    area_formacao = models.IntegerField(
        'Área de Formação', blank=False, null=True, help_text='A atividade profissional efetiva foi desenvolvida em sua área de formação?', choices=[[1, 'Sim'], [0, 'Não']]
    )
    contribuiu = models.IntegerField(
        'Contribuição', blank=False, null=True, help_text='As atividades desenvolvidas contribuíram para a sua ' 'formação?', choices=[[1, 'Sim'], [0, 'Não']]
    )
    aplicou_conhecimento = models.IntegerField(
        'Aplicação do Conhecimento',
        blank=False,
        null=True,
        help_text='Você teve oportunidade de aplicar os conhecimentos ' 'adquiridos no seu Curso?',
        choices=[[1, 'Sim'], [0, 'Não']],
    )

    # avaliação do aprendiz (somente relatório do aprendiz)
    avaliacao_conceito = models.IntegerField(
        'Conceito', help_text='Qual conceito você atribui ao desenvolvimento desta prática profissional?', choices=AVALICAO_CONCEITO_CHOICES, null=True, blank=False
    )

    # Dados gerais
    data_relatorio = models.DateFieldPlus('Data da Declaração de Realização de Atividade Profissional Efetiva', blank=False, null=True)

    class Meta:
        verbose_name = 'Atividade Profissional Efetiva'
        verbose_name_plural = 'Atividades Profissionais Efetivas'

    def __str__(self):
        return 'Atividade Profissional Efetiva do(a) aluno(a) {}'.format(self.aluno)

    def get_absolute_url(self):
        return '/estagios/atividade_profissional_efetiva/{}/'.format(self.pk)

    def get_situacao_aluno(self):
        return '{}'.format(self.aluno.situacao)

    get_situacao_aluno.admin_order_field = 'aluno__situacao__descricao'
    get_situacao_aluno.short_description = 'Situação da Matrícula no Curso'

    def get_situacao_ultima_matricula_periodo(self):
        return '{}'.format(self.aluno.get_ultima_matricula_periodo().situacao)

    get_situacao_ultima_matricula_periodo.admin_order_field = 'aluno__matriculaperiodo__situacao__descricao'
    get_situacao_ultima_matricula_periodo.short_description = 'Situação da Matrícula em Período'

    def get_campus(self):
        return '{}'.format(self.aluno.curso_campus.diretoria.setor.uo)

    get_campus.admin_order_field = 'aluno__curso_campus__diretoria__setor__uo'
    get_campus.short_description = 'Campus'

    def is_concluida(self):
        return self.situacao == self.CONCLUIDA

    def is_nao_concluida(self):
        return self.situacao == self.NAO_CONCLUIDA

    def is_encerrado(self):
        return self.situacao == self.CONCLUIDA or self.situacao == self.NAO_CONCLUIDA

    def is_cancelado(self):
        return self.situacao == self.NAO_CONCLUIDA

    def is_em_andamento(self):
        return self.situacao == self.EM_ANDAMENTO

    def get_email_aluno(self):
        if self.aluno.pessoa_fisica.email_secundario:
            return self.aluno.pessoa_fisica.email_secundario
        elif self.aluno.pessoa_fisica.email:
            return self.aluno.pessoa_fisica.email
        elif self.aluno.email_academico:
            return self.aluno.email_academico
        else:
            return None

    @transaction.atomic
    def save(self):
        if not self.pk:
            super().save()
            self.notificar_aluno_inicialmente()
            self.orientador_recem_cadastrado()
        super().save()

    def notificar_aluno_inicialmente(self, user=None):
        self.save()
        texto = (
            '<h1>Cadastro de Atividade Profissional Efetiva</h1>'
            '<p>Caro(a), {} ({}), você foi cadastrado(a) em uma atividade profissional efetiva, sob '
            'orientação de {}. É de sua responsabilidade o acompanhamento das etapas e realização dessa '
            'prática profissional. Você deve buscar orientação e comparecer às possíveis reuniões com o(a) orientador(a). </p>'
            '<p>Período da atividade profissional efetiva: de {} até {}.</p>'
            '<p>Ao final do período previsto em seu plano de atividades, você deve cadastrar o seu Relatório de '
            'Atividades Final, previamente aprovado por (ORIENTADOR). O envio desse relatório pode ser feito somente após o dia {}.</p>'
            '<p>Manual da atividade profissional efetiva: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/atividade-profissional-efetiva/manuais-suap/</p>'
            '<p>Mais informações sobre essa atividade estão disponíveis no seu SUAP > Menu Lateral > Ensino > Dados do Aluno > Aba: Estágios e Afins.</p>'
            '<p>Em caso de dúvidas, procure a Coordenação responsável por estágios no seu Campus.</p>'.format(
                self.aluno.pessoa_fisica.nome,
                self.aluno.matricula,
                self.orientador,
                format_(self.inicio),
                format_(self.data_prevista_encerramento),
                format_(self.data_prevista_encerramento),
            )
        )

        titulo = '[SUAP] Cadastro de Atividade Profissional Efetiva'

        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [self.aluno.get_vinculo()])

        email_aluno = self.get_email_aluno()
        if email_aluno:
            notificao = NotificacaoAtividadeProfissionalEfetiva(
                atividade_profissional_efetiva=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAtividadeProfissionalEfetiva.NOTIFICACAO_INICIAL,
                notificador=user,
                email_destinatario=email_aluno,
                mensagem_enviada='{}<br/>{}'.format(titulo, texto),
            )
            notificao.save()

    def orientador_recem_cadastrado(self, user=None):
        url_servidor = Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')
        texto = (
            '<h1>Cadastro como Orientador de Atividade Profissional Efetiva</h1>'
            '<p>Caro(a), {}, você foi cadastrado(a) como orientador(a) da atividade profissional efetiva de {}. '
            'É de sua responsabilidade o acompanhamento do desenvolvimento das atividades dessa prática profissional. '
            'Ressaltamos a possibilidade de utilização da funcionalidade: '
            '<a href="{}accounts/login/?next=/estagios/atividade_profissional_efetiva/{}/?tab=reunioes">Atividades de Orientação</a> '
            'com a qual é possível agendar (reuniões) e registrar as orientações realizadas com o(a) estudante.</p>'
            '<p/>Período da atividade profissional efetiva: de {} até {}.</p>'
            '<p>Também é função do orientador: acompanhar a elaboração e envio do Relatório de Atividades Final, além do registro da nota em diário específico.</p>'
            '<p>O relatório final poderá ser enviado após o dia {}.</p>'
            '<p>Manual do orientador: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/atividade-profissional-efetiva/manuais-suap/</p>'
            '<p>Mais informações sobre a atividade profissional efetiva estão disponíveis no seu SUAP> Serviços> Professor > Orientações de Estágio e Afins.</p>'
            '<p>Em caso de dúvidas, procure a Coordenação responsável por estágios no seu Campus.</p>'.format(
                self.orientador.vinculo.pessoa.nome,
                self.aluno,
                url_servidor,
                self.pk,
                format_(self.inicio),
                format_(self.data_prevista_encerramento),
                format_(self.data_prevista_encerramento),
            )
        )

        titulo = '[SUAP] Cadastro como Orientador de Atividade Profissional Efetiva'

        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
        if self.orientador.vinculo.user.email:
            notificao = NotificacaoAtividadeProfissionalEfetiva(
                atividade_profissional_efetiva=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAtividadeProfissionalEfetiva.NOTIFICACAO_INICIAL,
                notificador=user,
                email_destinatario=self.orientador.vinculo.user.email,
                mensagem_enviada='{}<br/>{}'.format(titulo, texto),
            )
            notificao.save()

    def notificar_orientador_envio_relatorio_final_aluno(self, user=None):
        url_servidor = Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')
        texto = (
            '<h1>Cadastro de Relatório Final de Atividade Profissional Efetiva</h1>'
            '<p>Caro(a), {}, informamos que o(a) estudante {}, o qual se encontra sob sua orientação numa '
            'atividade profissional efetiva, cadastrou o seu relatório final. A versão enviada pelo(a) '
            'aluno(a) deve ter sido autorizada e aprovada por você.</p>'
            '<p>Para verificar, acesse: '
            '<a href="{}accounts/login/?next=/estagios/atividade_profissional_efetiva/{}/?tab=relatorio">Relatório de Atividades - Aluno</a></p>'
            '<p>Em caso de dúvidas, favor procurar a Coordenação de Extensão/Estágios do seu Campus.</p>'.format(
                self.orientador.vinculo.pessoa.nome, self.aluno, url_servidor, self.pk
            )
        )

        titulo = '[SUAP] Cadastro de Relatório Final de Atividade Profissional Efetiva'

        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
        if self.orientador.vinculo.user.email:
            notificao = NotificacaoAtividadeProfissionalEfetiva(
                atividade_profissional_efetiva=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAtividadeProfissionalEfetiva.NOTIFICACAO_ENVIO_RELATORIO_FINAL_ALUNO,
                notificador=user,
                email_destinatario=self.orientador.vinculo.user.email,
                mensagem_enviada='{}<br/>{}'.format(titulo, texto),
            )
            notificao.save()

    def get_sugestao_ch_final(self):
        dias = numpy.busday_count(self.inicio, self.data_prevista_encerramento + datetime.timedelta(days=1))
        ch_sugerida = dias * (self.ch_semanal / 5.0)
        return (
            'Dada a data cadastrada de início e a data prevista para encerramento desta Atividade Profissional Efetiva, considerando-se apenas '
            'os dias de trabalho (segunda a sexta), estima-se uma carga horária de {} horas de trabalho. Deste '
            'total não são excluídos feriados e nem outras possíveis interrupções do trabalho na Instituição de Realização da Atividade.'.format(format_(ch_sugerida))
        )

    def get_periodo_duracao(self):
        if self.encerramento:
            return [self.inicio, self.encerramento]
        else:
            return [self.inicio, self.data_prevista_encerramento]

    def notificar(self, user=None):
        hoje = datetime.date.today()

        if self.situacao == self.EM_ANDAMENTO:
            self.verificar_matricula_irregular()

        if self.situacao == self.EM_ANDAMENTO and self.data_prevista_encerramento <= hoje and not self.relatorio_final_aluno:
            url_servidor = Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')
            titulo = '[SUAP] Pendência do Relatório Final do Aluno'
            assunto = (
                '<h1>Atividade Profissional Efetiva</h1>'
                '<h2>Pendência do Relatório Final do Aluno</h2>'
                '<p>Prezado(a) {}, tendo em vista o término do período de sua atividade profissional efetiva '
                '(de {} a {}), orientada por {}, solicitamos que seja devidamente registrado o relatório '
                'de atividades final, para que possamos proceder o encerramento da atividade.</p>'
                '<p>Para registrar o relatório, acesse o link a seguir: '
                '<a href="{}accounts/login/?next=/estagios/atividade_profissional_efetiva/{}/?tab=relatorios">Registrar Relatório</a></p>'
                '<p>Em caso de dúvidas, procure a Coordenação responsável por estágios no seu Campus.</p>'.format(
                    self.aluno.get_nome(), format_(self.inicio), format_(self.data_prevista_encerramento), self.orientador, url_servidor, self.pk
                )
            )

            send_notification(titulo, assunto, settings.DEFAULT_FROM_EMAIL, [self.aluno.get_vinculo()])
            email_aluno = self.get_email_aluno()
            if email_aluno:
                notificao = NotificacaoAtividadeProfissionalEfetiva(
                    atividade_profissional_efetiva=self,
                    data=datetime.datetime.now(),
                    tipo=NotificacaoAtividadeProfissionalEfetiva.NOTIFICACAO_RELATORIO_PENDENTE,
                    notificador=user,
                    email_destinatario=email_aluno,
                    mensagem_enviada='{}<br/>{}'.format(titulo, assunto),
                )
                notificao.save()

            assunto = (
                '<h1>Atividade Profissional Efetiva</h1>'
                '<h2>Pendência do Relatório Final do Aluno</h2>'
                '<p>Prezado(a) {}, tendo em vista o término do período da atividade profissional '
                'efetiva de {} (de {} a {}), sob sua orientação, solicitamos que '
                'verifique com o(a) estudante o registro do relatório de atividades final, para que '
                'possamos proceder o encerramento da atividade.</p>'
                '<p>Além disso, é interessante que seja verificada a existência de um diário '
                '(SUAP- Secretaria Acadêmica) para registro da nota correspondente ao relatório.</p>'
                '<p>Em caso de dúvidas, procure a Coordenação responsável por estágios no seu Campus.</p>'.format(
                    self.orientador.vinculo.pessoa.nome, self.aluno, format_(self.inicio), format_(self.data_prevista_encerramento)
                )
            )
            send_notification(titulo, assunto, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
            if self.orientador.vinculo.user.email:
                notificao = NotificacaoAtividadeProfissionalEfetiva(
                    atividade_profissional_efetiva=self,
                    data=datetime.datetime.now(),
                    tipo=NotificacaoAtividadeProfissionalEfetiva.NOTIFICACAO_RELATORIO_PENDENTE,
                    notificador=user,
                    email_destinatario=self.orientador.vinculo.user.email,
                    mensagem_enviada='{}<br/>{}'.format(titulo, assunto),
                )
                notificao.save()

    def verificar_matricula_irregular(self):
        # se ocorreu matrícula irregular por parte de um aluno
        if self.aluno.situacao in get_situacoes_irregulares() and not self.prazo_final_regularizacao_matricula_irregular:
            self.prazo_final_regularizacao_matricula_irregular = datetime.date.today() + relativedelta(days=7)
            self.save()
            self.notificar_aluno_matricula_irregular()
            self.notificar_orientador_aluno_matricula_irregular()
            self.notificar_coordenador_aluno_matricula_irregular()
            self.notificar_coordenacao_extensao_aluno_matricula_irregular()
        # se foi dado prazo e o aluno regularizou a matrícula
        if self.aluno.situacao not in get_situacoes_irregulares() and self.prazo_final_regularizacao_matricula_irregular:
            self.prazo_final_regularizacao_matricula_irregular = None
            self.save()
        # se a situacao irregular persistiu por mais de 7 dias
        if (
            self.aluno.situacao in get_situacoes_irregulares()
            and self.prazo_final_regularizacao_matricula_irregular
            and self.prazo_final_regularizacao_matricula_irregular < datetime.date.today()
            and not NotificacaoAtividadeProfissionalEfetiva.objects.filter(
                atividade_profissional_efetiva=self, tipo=NotificacaoAtividadeProfissionalEfetiva.NOTIFICACAO_INTERRUPCAO
            ).exists()
        ):
            self.situacao = self.NAO_CONCLUIDA
            self.save()
            self.notificar_aluno_interrupcao()
            self.notificar_orientador_interrupcao()

    def notificar_aluno_matricula_irregular(self, user=None):
        instituicao_sigla = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
        titulo = '[SUAP] Matrícula Irregular'
        mensagem = (
            '<h1>Atividade Profissional Efetiva</h1>'
            '<h2>Matrícula Irregular</h2>'
            '<p>Caro(a), {}, sua matrícula no curso {},  encontra-se com a seguinte situação irregular: <strong>{}</strong>. '
            'Verificamos que você possui uma atividade profissional efetiva '
            'com duração prevista até {}. A matrícula regular é '
            'pré-requisito para a manutenção desse cadastro, e conclusão da prática profissional.</p>'
            '<p>É necessário que você procure o {} (Secretaria Acadêmica e Setor de '
            'Estágios/Extensão) para regularizar sua situação até o dia {}.</p>'
            '<p>Caso não compareça, o seu cadastro será interrompido por situação de matrícula irregular.</p>'.format(
                self.aluno,
                self.aluno.curso_campus,
                self.aluno.situacao.descricao,
                format_(self.data_prevista_encerramento),
                instituicao_sigla,
                format_(self.prazo_final_regularizacao_matricula_irregular),
            )
        )

        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.aluno.get_vinculo()])
        email_aluno = self.get_email_aluno()
        if email_aluno:
            notificao = NotificacaoAtividadeProfissionalEfetiva(
                atividade_profissional_efetiva=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAtividadeProfissionalEfetiva.NOTIFICACAO_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=email_aluno,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_orientador_aluno_matricula_irregular(self, user=None):
        titulo = '[SUAP] Orientando com Matrícula Irregular'
        mensagem = (
            '<h1>Atividade Profissional Efetiva</h1>'
            '<h2>Orientando com Matrícula Irregular</h2>'
            '<p>Caro(a), {}, informamos que o(a) estudante {}, tem um cadastro de atividade profissional '
            'efetiva em aberto, sob sua orientação, e está com a seguinte situação irregular: <strong>{}</strong>. '
            'O(a) aluno(a) tem até o dia {} para regularizar sua matrícula junto a nossa instituição.</p>'
            '<p>Informamos que o encerramento desse cadastro é importante para a contabilização da carga '
            'horária de prática profissional. Caso o (a) aluno (a) não regularize sua situação, o cadastro '
            'será interrompido por motivo de matrícula irregular.</p>'
            '<p>É importante averiguar a situação em que se encontra o(a) estudante e entrar em contato com '
            'a Coordenação de Estágios/Extensão do Campus.</p>'.format(
                self.orientador.vinculo.pessoa.nome, self.aluno, self.aluno.situacao.descricao, format_(self.prazo_final_regularizacao_matricula_irregular)
            )
        )
        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
        if self.orientador.vinculo.user.email:
            notificao = NotificacaoAtividadeProfissionalEfetiva(
                atividade_profissional_efetiva=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAtividadeProfissionalEfetiva.NOTIFICACAO_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=self.orientador.vinculo.user.email,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_coordenador_aluno_matricula_irregular(self, user=None):
        titulo = '[SUAP] Aluno de Curso sob sua Coordenação com Matrícula Irregular'
        mensagem = (
            '<h1>Atividade Profissional Efetiva</h1>'
            '<h2>Aluno de Curso sob sua Coordenação com Matrícula Irregular</h2>'
            '<p>Caro(a), {}, informamos que o(a) estudante {}, tem um cadastro de atividade profissional '
            'efetiva em aberto, sob orientação de {}, e está com a seguinte situação irregular: <strong>{}</strong>. '
            'O(a) aluno(a) tem até o dia {} para regularizar sua matrícula junto a nossa instituição.</p>'
            '<p>Informamos que o encerramento desse cadastro é importante para a contabilização da carga '
            'horária de prática profissional. Caso o (a) aluno (a) não regularize sua situação, o cadastro '
            'será interrompido por motivo de matrícula irregular.</p>'
            '<p>É importante averiguar a situação em que se encontra o(a) estudante e entrar em contato com '
            'a Coordenação de Estágios/Extensão do Campus.</p>'.format(
                self.aluno.curso_campus.coordenador.nome, self.aluno, self.orientador, self.aluno.situacao.descricao, format_(self.prazo_final_regularizacao_matricula_irregular)
            )
        )

        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
        if self.aluno.curso_campus.coordenador.user.email:
            notificao = NotificacaoAtividadeProfissionalEfetiva(
                atividade_profissional_efetiva=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAtividadeProfissionalEfetiva.NOTIFICACAO_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=self.aluno.curso_campus.coordenador.user.email,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_coordenacao_extensao_aluno_matricula_irregular(self, user=None):
        coordenadores = get_coordenadores_estagio(self.aluno)
        coordenadores_nomes = get_coordenadores_nomes(coordenadores)
        coordenadores_emails = get_coordenadores_emails(coordenadores)
        coordenadores_vinculos = get_coordenadores_vinculos(coordenadores)
        instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
        titulo = '[SUAP] Atividade Profissional Efetiva com Matrícula Irregular'
        mensagem = (
            '<h1>Atividade Profissional Efetiva com Matrícula Irregular</h1>'
            '<p>Caros(as), Coordenadores(as) de Estágio {}, informamos que o(a) estudante {}, tem um cadastro de atividade profissional '
            'efetiva em aberto e está com a seguinte situação de matrícula irregular: <strong>{}</strong>. '
            'O(a) aluno(a) tem até o dia {} para regularizar sua matrícula junto ao {}. </p>'
            '<p>Informamos que o encerramento desse cadastro é importante para a contabilização da carga '
            'horária de prática profissional. Caso o (a) aluno (a) não regularize sua situação, o cadastro '
            'será interrompido por motivo de matrícula irregular.</p>'.format(
                coordenadores_nomes, self.aluno, self.aluno.situacao.descricao, format_(self.prazo_final_regularizacao_matricula_irregular), instituicao
            )
        )

        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, coordenadores_vinculos)
        if coordenadores_emails:
            notificao = NotificacaoAtividadeProfissionalEfetiva(
                atividade_profissional_efetiva=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAtividadeProfissionalEfetiva.NOTIFICACAO_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=coordenadores_emails,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def get_data_envio_notificacao(self):
        return self.prazo_final_regularizacao_matricula_irregular + relativedelta(days=-7)

    def notificar_aluno_interrupcao(self, user=None):
        titulo = '[SUAP] Interrupção de Atividade Profissional Efetiva'
        data_envio_notificacao = self.get_data_envio_notificacao()
        mensagem = (
            '<h1>Interrupção de Atividade Profissional Efetiva</h1>'
            '<p>Caro(a), {}, de acordo com aviso enviado no dia {}, e diante da ausência de manifestação de '
            'sua parte, informamos que o seu cadastro de atividade profissional efetiva será interrompido '
            'por motivo de matrícula irregular.</p>'.format(self.aluno, format_(data_envio_notificacao))
        )
        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.aluno.get_vinculo()])
        email_aluno = self.get_email_aluno()
        if email_aluno:
            notificao = NotificacaoAtividadeProfissionalEfetiva(
                atividade_profissional_efetiva=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAtividadeProfissionalEfetiva.NOTIFICACAO_INTERRUPCAO,
                notificador=None,
                email_destinatario=email_aluno,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_orientador_interrupcao(self, user=None):
        titulo = '[SUAP] Interrupção de Atividade Profissional Efetiva'
        mensagem = (
            '<h1>Interrupção de Atividade Profissional Efetiva</h1>'
            '<p>Caro(a), {}, informamos que o(a) estudante {}, o qual se encontra sob sua orientação, '
            'não se manifestou a respeito da condição irregular de sua matrícula: <strong>{}</strong>. Dessa forma, o '
            'cadastro de atividade profissional efetiva será interrompido por motivo de '
            'matrícula irregular.</p>'.format(self.orientador.vinculo.pessoa.nome, self.aluno, self.aluno.situacao.descricao)
        )

        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
        if self.orientador.vinculo.user.email:
            notificao = NotificacaoAtividadeProfissionalEfetiva(
                atividade_profissional_efetiva=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAtividadeProfissionalEfetiva.NOTIFICACAO_INTERRUPCAO,
                notificador=None,
                email_destinatario=self.orientador.vinculo.user.email,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()


class OrientacaoAtividadeProfissionalEfetiva(models.ModelPlus):
    atividade_profissional_efetiva = models.ForeignKeyPlus(AtividadeProfissionalEfetiva, verbose_name='Atividade Profissional Efetiva')
    orientador = models.ForeignKeyPlus(Professor, verbose_name='Orientador')
    data = models.DateFieldPlus(verbose_name='Data da Orientação')
    meio = models.CharFieldPlus('Meio/Modalidade Utilizada', blank=True, null=True, help_text='E-mail, presencial, reunião, etc.')
    hora_inicio = models.TimeFieldPlus('Hora de Início')
    local = models.CharFieldPlus('Local', blank=True, null=True)
    descricao = models.TextField('Descrição do Conteúdo da Orientação', blank=True, null=True)

    class Meta:
        ordering = ('-data',)

    def save(self):
        if self.data and (self.data > datetime.date.today() or (self.data == datetime.date.today() and self.hora_inicio > datetime.datetime.now().time())):
            url_servidor = Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')
            titulo = '[SUAP] Orientação de Atividade Profissional Efetiva Agendada'
            texto = (
                '<h1>Orientação de Atividade Profissional Efetiva Agendada</h1>'
                '<p>Caro(a), {}, uma orientação de atividade profissional efetiva foi '
                'registrada, para verificar, acesse seu SUAP ou clique no link: '
                '<a href="{}accounts/login/?next=/estagios/pratica_profissional/{}/?tab=reunioes">Orientações</a></p>'.format(
                    self.atividade_profissional_efetiva.aluno, url_servidor, self.atividade_profissional_efetiva.pk
                )
            )

            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [self.atividade_profissional_efetiva.aluno.get_vinculo()])
            email_aluno = self.atividade_profissional_efetiva.get_email_aluno()
            if email_aluno:
                notificao = NotificacaoAtividadeProfissionalEfetiva(
                    atividade_profissional_efetiva=self.atividade_profissional_efetiva,
                    data=datetime.datetime.now(),
                    tipo=NotificacaoAtividadeProfissionalEfetiva.NOTIFICACAO_AGENDAMENTO_ORIENTACAO,
                    notificador=self.user,
                    email_destinatario=email_aluno,
                    mensagem_enviada='{}<br/>{}'.format(titulo, texto),
                )
                notificao.save()
        super().save()

    def __str__(self):
        return 'Orientação de Atividade Profissional Efetiva (data: {}, hora: {}:{}, local: {})'.format(
            format_(self.data), self.hora_inicio.hour, self.hora_inicio.minute, self.local
        )


class NotificacaoAtividadeProfissionalEfetiva(models.ModelPlus):
    NOTIFICACAO_INICIAL = 1
    NOTIFICACAO_RELATORIO_PENDENTE = 2
    NOTIFICACAO_MATRICULA_IRREGULAR = 3
    NOTIFICACAO_INTERRUPCAO = 4
    NOTIFICACAO_ENVIO_RELATORIO_FINAL_ALUNO = 5
    NOTIFICACAO_AGENDAMENTO_ORIENTACAO = 6
    NOTIFICACAO_NECESSIDADE_ATUALIZACAO_PAE = 7

    TIPO_CHOICES = [
        [NOTIFICACAO_INICIAL, 'Notificação inicial.'],
        [NOTIFICACAO_RELATORIO_PENDENTE, 'Notificação de Pendência de Relatório do Aluno.'],
        [NOTIFICACAO_MATRICULA_IRREGULAR, 'Notificação de Matrícula Irregular do Aluno.'],
        [NOTIFICACAO_INTERRUPCAO, 'Notificação de Interrupção do Cadastro de Atividade Profissional Efetiva.'],
        [NOTIFICACAO_ENVIO_RELATORIO_FINAL_ALUNO, 'Notificação de Cadastro de Relatório Final de Atividade Profissional Efetiva.'],
        [NOTIFICACAO_AGENDAMENTO_ORIENTACAO, 'Notificação de Agendamento de Orientação.'],
        [NOTIFICACAO_NECESSIDADE_ATUALIZACAO_PAE, 'Notificação de Necessidade de Atualização do Plano de Atividades de Estágio.'],
    ]

    atividade_profissional_efetiva = models.ForeignKeyPlus(AtividadeProfissionalEfetiva, verbose_name='Atividade Profissional Efetiva')
    notificador = models.ForeignKeyPlus('comum.User', verbose_name='Notificador', null=True)
    data = models.DateTimeFieldPlus('Data da Notificação')
    tipo = models.IntegerField('Tipo', choices=TIPO_CHOICES)
    email_destinatario = models.TextField('E-mail')
    mensagem_enviada = models.TextField('Mensagem Enviada')

    class Meta:
        ordering = ('-data',)
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'

    def __str__(self):
        return '{}-{}'.format(self.pk, self.get_tipo_display())


class Aprendizagem(models.ModelPlus):
    CONCLUSAO = 1
    RESCISAO = 2
    ENCERRAMENTO_CHOICES = [[CONCLUSAO, 'Conclusão'], [RESCISAO, 'Rescisão']]

    MOTIVO_POR_TERMINO_CONTRATO = 1
    MOTIVO_CONTRATACAO_CONCEDENTE = 2
    MOTIVO_DESEMPENHO_INSUFICIENTE_INADAPTACAO = 3
    MOTIVO_RESCISAO_FALTA_DISCIPLINAR = 4
    MOTIVO_RESCISAO_AUSENCIA_INJUSTIFICADA = 5
    MOTIVO_RESCISAO_24_ANOS = 6
    MOTIVO_RESCISAO_A_PEDIDO_APRENDIZ = 7
    MOTIVO_CONCEDENTE_ENCERROU_ATIVIDADES = 8
    MOTIVACAO_DESLIGAMENTO_ENCERRAMENTO_CHOICHES = [
        [MOTIVO_POR_TERMINO_CONTRATO, 'Término do contrato.'],
        [MOTIVO_CONTRATACAO_CONCEDENTE, 'Contratação pela Concedente'],
        [MOTIVO_DESEMPENHO_INSUFICIENTE_INADAPTACAO, 'Rescisão por desempenho insuficiente ou inadaptação do aprendiz.'],
        [MOTIVO_RESCISAO_FALTA_DISCIPLINAR, 'Rescisão por falta disciplinar grave.'],
        [MOTIVO_RESCISAO_AUSENCIA_INJUSTIFICADA, 'Rescisão por ausência injustificada à escola que implique perda do ano letivo.'],
        [MOTIVO_RESCISAO_24_ANOS, 'Rescisão porque aprendiz atingiu 24 anos.'],
        [MOTIVO_RESCISAO_A_PEDIDO_APRENDIZ, 'Rescisão a pedido do aprendiz.'],
        [MOTIVO_CONCEDENTE_ENCERROU_ATIVIDADES, 'Concedente encerrou suas atividades.'],
    ]

    MENSAL = 1
    QUINZENAL = 2
    PERIODICIDADE_CHOICES = [[MENSAL, 'Mensal'], [QUINZENAL, 'Quinzenal']]

    # Dados Gerais
    aprendiz = models.ForeignKeyPlus(Aluno, verbose_name='Aprendiz')
    convenio = models.ForeignKeyPlus(Convenio, verbose_name='Convênio', null=True, blank=True)
    turno = models.ForeignKeyPlus(Turno, verbose_name='Turno', on_delete=models.CASCADE)
    empresa = models.ForeignKeyPlus(
        PessoaJuridica, verbose_name='Concedente', help_text='Para adicionar um concedente de aprendizagem, acesse o menu Administração -> Cadastros -> Pessoas Jurídicas.'
    )
    cidade = models.ForeignKeyPlus('edu.Cidade', verbose_name='Município', null=True, on_delete=models.CASCADE)
    logradouro = models.CharFieldPlus('Logradouro', null=True)
    numero = models.CharField('Nº', max_length=50, null=True)
    complemento = models.CharFieldPlus('Complemento', null=True, blank=True)
    bairro = models.CharFieldPlus('Bairro', null=True)
    cep = models.CharField('CEP', max_length=9, null=True)

    orientador = models.ForeignKeyPlus(Professor, verbose_name='Professor Orientador')

    # remuneracao
    auxilio_transporte = models.DecimalFieldPlus(verbose_name='Auxílio Transporte (R$)', null=True, blank=True)
    outros_beneficios = models.DecimalFieldPlus(verbose_name='Outros Benefícios (R$)', null=True, blank=True)
    descricao_outros_beneficios = models.TextField('Descrição dos Outros Benefícios', null=True, blank=True)

    # Período
    # data_inicio = models.DateFieldPlus(u'Data de Início')
    # data_prevista_fim = models.DateFieldPlus(u'Data Prevista para Encerramento')

    # Documentação
    contrato_aprendizagem = models.FileFieldPlus('Contrato de Aprendizagem', blank=False, max_length=255, upload_to='aprendizagem/contrato_aprendizagem')
    carteira_trabalho = models.FileFieldPlus(
        'Anotação na Carteira de Trabalho',
        blank=False,
        max_length=255,
        upload_to='aprendizagem/carteira_trabalho',
        help_text='Dever ser inserida comprovação de que o contrato foi anotado na carteira de trabalho do aprendiz.',
    )
    resumo_curso = models.FileFieldPlus(
        'Resumo do Curso de Aprendizagem',
        blank=False,
        max_length=255,
        upload_to='aprendizagem/resumo_curso',
        help_text='O resumo do curso encontra-se na plataforma: www.juventudeweb.mte.gov.br',
    )

    # Prática Profissional
    eh_utilizado_como_pratica_profissional = models.BooleanField('A aprendizagem será utilizada como prática profissional?')
    plano_atividades = models.FileFieldPlus(
        'Plano de Atividades',
        blank=True,
        max_length=255,
        upload_to='aprendizagem/planos_atividades',
        help_text='Plano de Atividades de acordo com a Resolução 25/2019, modelo disponível no endereço: http://portal.ifrn.edu.br/extensao/estagios-e-egressos',
    )

    # Empregado Monitor
    nome_monitor = models.CharFieldPlus('Nome', blank=False)
    telefone_monitor = models.CharFieldPlus('Telefone', null=True, blank=True)
    cargo_monitor = models.CharFieldPlus('Cargo', blank=False)
    email_monitor = models.CharFieldPlus('E-mail', blank=False, help_text='Este e-mail será importante para o envio da avaliação.')
    observacao = models.TextField('Observação', blank=True)

    # Módulo I
    modulo_1 = models.BooleanField('O aluno fará o módulo I?')

    # Módulo II
    modulo_2 = models.BooleanField('O aluno fará o módulo II?')

    # Módulo III
    modulo_3 = models.BooleanField('O aluno fará o módulo III?')

    # Módulo IV
    modulo_4 = models.BooleanField('O aluno fará o módulo IV?')

    # Encerramento: Dados do Encerramento
    encerramento_por = models.IntegerField('Encerramento por', choices=ENCERRAMENTO_CHOICES, null=True, blank=False)
    motivo_encerramento = models.IntegerField('Motivo do Encerramento', choices=MOTIVACAO_DESLIGAMENTO_ENCERRAMENTO_CHOICHES, null=True, blank=False)
    motivacao_rescisao = models.TextField(
        'Observações', null=True, blank=True, help_text='Inserir o motivo da rescisão, do encerramento com pendência ou outras informações relevantes.'
    )
    data_encerramento = models.DateFieldPlus('Data do Encerramento', null=True, blank=False)
    ch_final = models.IntegerField('Carga-Horária Prática Final', null=True, blank=False)

    # Encerramento: Documentação
    laudo_avaliacao = models.FileFieldPlus(
        'Laudo de Avaliação',
        blank=True,
        max_length=255,
        upload_to='aprendizagem/laudo_avaliacao',
        help_text='Documento necessário somente em caso de rescisão por desempenho insuficiente ou inadaptação do aprendiz.',
    )
    comprovante_encerramento = models.FileFieldPlus(
        'Comprovante de Encerramento',
        null=True,
        blank=False,
        max_length=255,
        upload_to='aprendizagem/comprovante_encerramento',
        help_text='Inserir a folha da carteira de trabalho que comprova o registro do encerramento do contrato com a sua respectiva data.',
    )
    codigo_verificador = models.TextField(default='')

    # Prazo para regularizar a matrícula
    prazo_final_regularizacao_matricula_irregular = models.DateFieldPlus('Prazo Final para Regularizar a Matrícula', null=True, blank=True)
    desvinculado_matricula_irregular = models.BooleanField('Aluno Desvinculado por Matrícula Irregular', help_text='Selecione para o caso de abandono do aluno.', default=False)

    periodicidade_envio_relatorio_frequencia = models.PositiveIntegerFieldPlus(
        'Periodicidade de Envio do Relatório de Frequência', choices=PERIODICIDADE_CHOICES, null=True, blank=True
    )
    dia_inicio_apuracao_frequencia = models.PositiveIntegerFieldPlus(
        'Dia de Inicial do Período de Apuração',
        choices=[[dia, dia] for dia in range(1, 32, 1)],
        null=True,
        blank=True,
        help_text='Dia em cada mês a partir do qual a empresa contabiliza o ponto dos aprendizes num período mensal '
        'ou quinzenal, no qual serão apuradas suas faltas na instituição de ensino. Exemplo: Se for '
        'escolhida uma periodicidade Quinzenal e como Dia Inicial o dia 3, o primeiro período de '
        'apuração das faltas será do dia 3 ao dia 18 e o segundo período será do dia 19 ao dia 2 '
        'do mês seguinte. Como consequência, o relatório será enviado no dia 3 do mês seguinte',
    )

    inicio_periodo_frequencia_1 = models.PositiveIntegerFieldPlus('Início do 1º Período', choices=[[dia, dia] for dia in range(1, 32, 1)], null=True, blank=True)
    fim_periodo_frequencia_1 = models.PositiveIntegerFieldPlus('Fim do 1º Período', choices=[[dia, dia] for dia in range(1, 32, 1)], null=True, blank=True)
    inicio_periodo_frequencia_2 = models.PositiveIntegerFieldPlus('Início do 2º Período (quinzenal)', choices=[[dia, dia] for dia in range(1, 32, 1)], null=True, blank=True)
    fim_periodo_frequencia_2 = models.PositiveIntegerFieldPlus(
        'Fim do 2º Período (quinzenal)', choices=[[dia, dia] for dia in range(1, 32, 1)], help_text='Preencher somente se o relatório for ' 'quinzenal.', null=True, blank=True
    )
    emails_relatorio_frequencia = models.TextField(
        'E-mails para Envio do Relatório de Frequência',
        null=True,
        blank=True,
        help_text='Informe o(s) e-mail(s), separados por virgula, para o(s) quais será enviado o relatório de '
        'frequência do aprendiz. Exemplo: rh@empresa.com.br, coordenador_estagio@ifrn.edu.br, '
        'monitor@empresa.com.br',
    )

    class Meta:
        verbose_name = 'Aprendizagem'
        verbose_name_plural = 'Aprendizagens'

    def __str__(self):
        return 'Aprendizagem do aluno {} na concedente {}'.format(self.aprendiz, self.empresa)

    def get_absolute_url(self):
        return '/estagios/aprendizagem/{}/'.format(self.pk)

    def clean(self):
        if self.eh_utilizado_como_pratica_profissional and not self.plano_atividades:
            raise ValidationError({'plano_atividades': 'O plano de atividades é obrigatório no caso da aprendizagem ser utizada como prática profissional.'})
        if hasattr(self, 'aprendiz'):
            if self.aprendiz and not self.aprendiz.matriz:
                raise ValidationError({'aprendiz': 'Aluno sem matriz não pode ser cadastrado.'})

            if not self.pk and self.aprendiz and self.aprendiz.situacao in get_situacoes_irregulares():
                raise ValidationError({'aprendiz': 'Aluno com situação {} não pode estagiar.'.format(self.aprendiz.situacao.descricao)})

            if self.aprendiz and self.aprendiz.curso_campus.modalidade not in Modalidade.objects.filter(
                id__in=[
                    Modalidade.LICENCIATURA,
                    Modalidade.ENGENHARIA,
                    Modalidade.BACHARELADO,
                    Modalidade.INTEGRADO,
                    Modalidade.INTEGRADO_EJA,
                    Modalidade.SUBSEQUENTE,
                    Modalidade.CONCOMITANTE,
                    Modalidade.TECNOLOGIA,
                ]
            ):
                raise ValidationError(
                    {
                        'aprendiz': 'Este aluno é da modalidade {}. Somente alunos das modalidades Licenciatura, Engenharia, Integrado, Integrado Eja, Subsequente e Tecnologia podem participar de programa de aprendizagem.'.format(
                            self.aprendiz.curso_campus.modalidade.descricao
                        )
                    }
                )

    @transaction.atomic
    def save(self):
        if not self.codigo_verificador:
            self.codigo_verificador = hashlib.sha1('{}{}{}'.format(self.orientador.pk, datetime.datetime.now(), settings.SECRET_KEY).encode()).hexdigest()
        super().save()

    def notificar_professores_diarios(self, user=None):
        professores = Professor.objects.filter(
            professordiario__diario__matriculadiario__matricula_periodo__pk=self.aprendiz.get_ultima_matricula_periodo().pk,
            professordiario__diario__matriculadiario__situacao=MatriculaDiario.SITUACAO_CURSANDO,
        ).distinct()
        emails_professores = professores.values_list('vinculo__user__email', flat=True)
        titulo = '[SUAP] Notificação de Aluno Aprendiz'
        mensagem = (
            '<h1>Notificação de Aluno Aprendiz</h1>'
            '<p>Prezados professores(as), o aluno(a) {} está em um programa de aprendizagem, por isso é necessário que, no mínimo, '
            'este(a) aluno(a) tenha sua frequência registrada no SUAP até o último dia útil do mês.</p>'.format(self.aprendiz)
        )
        vinculos = []
        for professor in professores:
            vinculos.append(professor.vinculo)

        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, vinculos)

        notificao = NotificacaoAprendizagem(
            aprendizagem=self,
            data=datetime.datetime.now(),
            tipo=NotificacaoAprendizagem.NOTIFICACAO_INICIAL_PROFESSORES_DIARIOS,
            notificador=user,
            email_destinatario=', '.join(emails_professores),
            mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
        )
        notificao.save()

    def get_campus(self):
        return '{}'.format(self.aprendiz.curso_campus.diretoria.setor.uo)

    get_campus.admin_order_field = 'aprendiz__curso_campus__diretoria__setor__uo'
    get_campus.short_description = 'Campus'

    def get_situacao_aluno(self):
        return '{}'.format(self.aprendiz.situacao)

    get_situacao_aluno.admin_order_field = 'aprendiz__situacao__descricao'
    get_situacao_aluno.short_description = 'Situação do Aprendiz'

    def get_situacao_ultima_matricula_periodo(self):
        return '{}'.format(self.aprendiz.get_ultima_matricula_periodo().situacao)

    get_situacao_ultima_matricula_periodo.admin_order_field = 'aprendiz__matriculaperiodo__situacao__descricao'
    get_situacao_ultima_matricula_periodo.short_description = 'Situação da Matrícula no Período'

    def get_email_aprendiz(self):
        if self.aprendiz.pessoa_fisica.email_secundario:
            return self.aprendiz.pessoa_fisica.email_secundario
        elif self.aprendiz.pessoa_fisica.email:
            return self.aprendiz.pessoa_fisica.email
        elif self.aprendiz.email_academico:
            return self.aprendiz.email_academico
        else:
            return None

    def enviar_email_empregado_monitor_recem_cadastrado(self, user=None):
        titulo = '[SUAP] Cadastro como Empregado Monitor de Aprendizagem'
        texto = (
            '<h1>Cadastro como Empregado Monitor de Aprendizagem</h1>'
            '<p>Caro(a), {}, você foi cadastrado(a) como empregado monitor(a) da aprendizagem do(a) aluno(a) {}.</p>'
            '<p>Você é responsável por acompanhar o desenvolvimento das atividades da aprendizagem e realizar em nosso sistema, '
            'os Relatórios de Atividades.</p>'
            '<p>Em cada período de referência para o envio dos desses relatórios, você receberá um '
            'e-mail com as informações de acesso ao sistema.</p>'.format(self.nome_monitor, self.aprendiz)
        )
        texto += '<p>Para mais esclarecimentos acesse o Manual do Empregado Monitor através do link: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/aprendizagem/manuais-usuarios</p>'
        texto += (
            '<p>Caso necessite entrar em contato conosco basta buscar o telefone do campus na página: www.ifrn.edu.br ou no contrato de aprendizagem assinado, '
            ', ou, ainda, entrar em contato com o professor orientador, através do seguinte e-mail: {}.</p>'.format(self.orientador.vinculo.pessoa.email)
        )
        texto += '<p>Desde já agradecemos sua contribuição com nosso aluno.</p>'
        send_mail(titulo, texto, settings.DEFAULT_FROM_EMAIL, [self.email_monitor])
        notificao = NotificacaoAprendizagem(
            aprendizagem=self,
            data=datetime.datetime.now(),
            tipo=NotificacaoAprendizagem.NOTIFICACAO_INICIAL,
            notificador=user,
            email_destinatario=self.email_monitor,
            mensagem_enviada='{}<br/>{}'.format(titulo, texto),
        )
        notificao.save()

    def enviar_email_orientador_recem_cadastrado(self, user=None):
        titulo = '[SUAP] Cadastro como Orientador de Aprendizagem'
        texto = (
            '<h1>Cadastro como Orientador de Aprendizagem</h1>'
            '<p>Caro(a), {}, você foi cadastrado(a) como orientador(a) de aprendizagem de {}. '
            'Você é o responsável na instituição de ensino pelo acompanhamento do desenvolvimento das atividades de aprendizagem,'
            'poderá realizar visitas e cadastrá-las em nosso sistema, além de acompanhar '
            'a elaboração e envio dos relatórios de atividades de aprendizagem.</p>'.format(self.orientador.vinculo.pessoa.nome, self.aprendiz.__str__())
        )
        texto += (
            '<p>Para mais esclarecimentos acesse o Manual do Orientador através do link: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/aprendizagem/manuais-usuarios</p>'
        )
        texto += '<p>Mais informações sobre a aprendizagem estão disponíveis em SUAP > Serviços > Professor > Orientações de Estágios e Afins.</p>'
        texto += '<p>Em caso de dúvidas, procure a Coordenação responsável por estágios no seu Campus.</p>'

        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
        if self.orientador.vinculo.user.email:
            notificao = NotificacaoAprendizagem(
                aprendizagem=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAprendizagem.NOTIFICACAO_INICIAL,
                notificador=user,
                email_destinatario=self.orientador.vinculo.user.email,
                mensagem_enviada='{}<br/>{}'.format(titulo, texto),
            )
            notificao.save()

    def enviar_email_aprendiz_recem_cadastrado(self, user=None):
        titulo = '[SUAP] Cadastro de Aprendizagem'
        texto = (
            '<h1>Cadastro de Aprendizagem</h1>'
            '<p>Caro(a), {}, você foi cadastrado(a) como aprendiz, sob orientação do(a) professor(a) {}. '
            'Você é responsável também pelo acompanhamento do andamento de sua aprendizagem. </p>'.format(self.aprendiz, self.orientador.vinculo.pessoa.nome)
        )
        texto += (
            '<p>Para mais esclarecimentos acesse o Manual do Aprendiz através do link: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/aprendizagem/manuais-usuarios</p>'
        )
        texto += '<p>Mais informações sobre o seu estágio estão disponíveis no seu SUAP> Menu Lateral> Ensino> Dados do Aluno> Aba: Estágios e Afins</p>'
        texto += '<p>Em caso de dúvidas, procure a Coordenação responsável por estágios no seu Campus.</p>'

        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [self.aprendiz.get_vinculo()])
        email_aprendiz = self.get_email_aprendiz()
        if email_aprendiz:
            notificao = NotificacaoAprendizagem(
                aprendizagem=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAprendizagem.NOTIFICACAO_INICIAL,
                notificador=user,
                email_destinatario=email_aprendiz,
                mensagem_enviada='{}<br/>{}'.format(titulo, texto),
            )
            notificao.save()

    @property
    def get_relatorios_estagiario(self):
        return RelatorioModuloAprendizagem.objects.filter(modulo_aprendizagem__aprendizagem=self, eh_relatorio_do_empregado_monitor=False).order_by('modulo_aprendizagem__inicio')

    def get_sugestao_ch_final(self):
        dias_modulo = 0
        ch_sugerida = 0
        for modulo in self.moduloaprendizagem_set.all():
            dias_modulo = numpy.busday_count(modulo.inicio, modulo.fim + datetime.timedelta(days=1))
            ch_sugerida = ch_sugerida + dias_modulo * (modulo.ch_pratica_semanal / 5.0)

        return (
            'Para cada módulo desta aprendizagem, dada a data cadastrada de início e a data prevista para o fim, '
            'considerando que a carga horária semanal é distribuída igualmente em todos os dias de trabalho, '
            'considerando-se dias de trabalho apenas o intervalo de segunda a sexta, estima-se uma carga horária '
            'prática de {} horas. Desse total não são excluídos feriados e nem outras possíveis interrupções das '
            'atividades na concedente.'.format(format_(ch_sugerida))
        )

    def ha_pendencia_de_visita(self, data_considerada=None):
        if not data_considerada:
            data_considerada = datetime.date.today()

        if self.data_encerramento:
            return False
        for modulo in self.moduloaprendizagem_set.all():
            if not modulo.visitaaprendizagem_set.exists() and not modulo.justificativavisitamoduloaprendizagem_set.exists() and modulo.fim <= data_considerada:
                return True
        return False

    def ha_pendencia_relatorio_monitor(self, data_considerada=None):
        if not data_considerada:
            data_considerada = datetime.date.today()

        if self.data_encerramento:
            return False
        for modulo in self.moduloaprendizagem_set.all():
            if not modulo.tem_relatorio_monitor() and modulo.fim <= data_considerada:
                return True
        return False

    def ha_pendencia_relatorio_aprendiz(self, data_considerada=None):
        if not data_considerada:
            data_considerada = datetime.date.today()

        if self.data_encerramento:
            return False
        for modulo in self.moduloaprendizagem_set.all():
            if not modulo.tem_relatorio_aprendiz() and modulo.fim <= data_considerada:
                return True
        return False

    @property
    def qtd_relatorios_aprendiz_pendentes(self):
        if self.data_encerramento:
            return 0
        qtd = 0
        for modulo in self.moduloaprendizagem_set.all():
            if not modulo.tem_relatorio_aprendiz() and modulo.fim < datetime.date.today():
                qtd += 1
        return qtd

    def resumo_pendencias(self):
        if self.data_encerramento:
            retorno = 'Encerrado'

        pendencias = []
        if self.ha_pendencia_relatorio_aprendiz():
            pendencias.append('de relatório do aprendiz')
        if self.ha_pendencia_relatorio_monitor():
            pendencias.append('de relatório do monitor')
        if pendencias:
            pendencias = ', '.join(pendencias)
            retorno = 'Pendências: {}'.format(pendencias)
        else:
            retorno = 'Sem pendências'
        return mark_safe(retorno)

    resumo_pendencias.short_description = 'Resumo de Pendências'

    def verificar_pendencias(self):
        if not self.data_encerramento:
            self.notificar_pendencia_avaliacao_modulo_monitor()
            self.notificar_pendencia_avaliacao_modulo_aprendiz()

    def notificar(self):
        if not self.data_encerramento:
            self.notificar_pendencia_avaliacao_modulo_monitor(deve_notificar_se_pendente=True)
            self.notificar_pendencia_avaliacao_modulo_aprendiz(deve_notificar_se_pendente=True)
            self.verificar_matricula_irregular()
            self.verificar_envio_relatorio_frequencia()

    def verificar_visitas_pendentes(self, deve_notificar_se_pendente=False, user=None):
        hoje = datetime.date.today()
        for modulo in self.moduloaprendizagem_set.all():
            if not modulo.visitaaprendizagem_set.exists() and modulo.inicio < hoje:
                if self.deve_enviar_primeira_notificacao_de_visita(modulo) or self.deve_enviar_segunda_notificacao_de_visita(modulo):
                    url_servidor = Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')
                    titulo = '[SUAP] Lembrete de Visita de Orientação de Aprendizagem'
                    assunto = (
                        '<h1>Aprendizagens</h1>'
                        '<h2>Notificação de Visita Pendente</h2>'
                        '<p>Prezado(a) orientador(a), de acordo com as informações enviadas no momento de cadastro da aprendizagem de {}, deve ser realizada e registrada ao menos uma visita durante o período do {}.</p>'
                        '<p>Caso não tenha realizado a visita, por favor, entrar em contato com a concedente para proceder o agendamento.</p>'
                        '<p>Essa aprendizagem se iniciou em {} e está prevista para finalizar em {}.</p>'
                        '<p>Informamos que a visita deve ser registrada em formulário próprio disponível no link: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/aprendizagem/formularios/</p>'
                        '<p>Para registrar a visita, acesse o link a seguir: '
                        '<a href="{}accounts/login/?next=/estagios/aprendizagem/{}/?tab=visitas">Visitas</a>.</p>'
                        '<p>Em caso de dúvidas, procure a Coordenação responsável por estágios no seu Campus.</p>'.format(
                            self.aprendiz, modulo, format_(self.get_data_inicio()), format_(self.get_data_prevista_encerramento()), url_servidor, self.pk
                        )
                    )
                    send_notification(titulo, assunto, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
                    if self.orientador.vinculo.user.email:
                        notificacao = NotificacaoAprendizagem(
                            aprendizagem=self,
                            data=datetime.datetime.now(),
                            tipo=NotificacaoAprendizagem.NOTIFICACAO_VISITA,
                            notificador=user,
                            email_destinatario=self.orientador.vinculo.user.email,
                            mensagem_enviada='{}<br/>{}'.format(titulo, assunto),
                        )
                        notificacao.save()
                        modulo_notificado = ModuloComPendenciaNotificado(modulo=modulo, notificacao=notificacao)
                        modulo_notificado.save()
                elif self.deve_enviar_notificacao_apos_fim_periodo(modulo) or (modulo.fim < hoje and deve_notificar_se_pendente):
                    url_servidor = Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')
                    titulo = '[SUAP] Pendência de Registro de Visita'
                    assunto = (
                        '<h1>Aprendizagens</h1>'
                        '<h2>Notificação de Visita Pendente</h2>'
                        '<p>Prezado(a) orientador(a), solicitamos que registre a visita à concedente da aprendizagem de {}.</p>'
                        '<p>Essa aprendizagem se iniciou em {} e está prevista para finalizar em {}.</p>'
                        '<p>Essa visita se refere ao {}.</p>'
                        '<p>Informamos que a visita deve ser registrada em formulário próprio disponível no link: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/aprendizagem/formularios/</p>'
                        '<p>Para registrar a visita, acesse o link a seguir: '
                        '<a href="{}accounts/login/?next=/estagios/aprendizagem/{}/?tab=visitas">Visitas</a>.</p>'
                        '<p>Obs.: Caso não tenha realizado a visita, por favor, entrar em contato com a coordenação responsável por estágios para proceder a justificativa de decurso de prazo formal, que também deve ser registrada no SUAP.</p>'
                        '<p>Em caso de dúvidas, procure a Coordenação responsável por estágios no seu Campus.</p>'.format(
                            self.aprendiz, format_(self.get_data_inicio()), format_(self.get_data_prevista_encerramento()), modulo, url_servidor, self.pk
                        )
                    )
                    send_notification(titulo, assunto, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
                    if self.orientador.vinculo.user.email:
                        notificacao = NotificacaoAprendizagem(
                            aprendizagem=self,
                            data=datetime.datetime.now(),
                            tipo=NotificacaoAprendizagem.NOTIFICACAO_VISITA,
                            notificador=user,
                            email_destinatario=self.orientador.vinculo.user.email,
                            mensagem_enviada='{}<br/>{}'.format(titulo, assunto),
                        )
                        notificacao.save()
                        modulo_notificado = ModuloComPendenciaNotificado(modulo=modulo, notificacao=notificacao)
                        modulo_notificado.save()

    def deve_enviar_primeira_notificacao_de_visita(self, modulo):
        def dia_inicial_para_envio(modulo):
            return modulo.inicio + (modulo.fim - modulo.inicio) / 3

        def dia_final_para_envio(modulo):
            return modulo.inicio + 2 * (modulo.fim - modulo.inicio) / 3 - relativedelta(days=1)

        if (
            datetime.date.today() >= dia_inicial_para_envio(modulo)
            and datetime.date.today() < dia_final_para_envio(modulo)
            and not ModuloComPendenciaNotificado.objects.filter(
                notificacao__aprendizagem=self, modulo=modulo, notificacao__data__date__gte=dia_inicial_para_envio(modulo), notificacao__data__date__lt=dia_final_para_envio(modulo)
            ).exists()
        ):
            return True
        else:
            return False

    def deve_enviar_segunda_notificacao_de_visita(self, modulo):
        def dia_inicial_para_envio(modulo):
            return modulo.inicio + 2 * (modulo.fim - modulo.inicio) / 3

        def dia_final_para_envio(modulo):
            return modulo.fim

        if (
            datetime.date.today() >= dia_inicial_para_envio(modulo)
            and datetime.date.today() <= dia_final_para_envio(modulo)
            and not ModuloComPendenciaNotificado.objects.filter(
                notificacao__aprendizagem=self,
                modulo=modulo,
                notificacao__data__date__gte=dia_inicial_para_envio(modulo),
                notificacao__data__date__lte=dia_final_para_envio(modulo),
            ).exists()
        ):
            return True
        else:
            return False

    def deve_enviar_notificacao_apos_fim_periodo(self, modulo):
        if (
            datetime.date.today() > modulo.fim
            and not ModuloComPendenciaNotificado.objects.filter(
                notificacao__aprendizagem=self, modulo=modulo, notificacao__data__date__gt=datetime.date.today() + relativedelta(days=-10)
            ).exists()
        ):
            return True
        else:
            return False

    def notificar_pendencia_avaliacao_modulo_monitor(self, deve_notificar_se_pendente=False, user=None):
        hoje = datetime.date.today()
        for modulo in self.moduloaprendizagem_set.all():
            if (
                not modulo.tem_relatorio_monitor()
                and modulo.fim < hoje
                and (
                    deve_notificar_se_pendente
                    or not ModuloComPendenciaNotificado.objects.filter(
                        modulo=modulo,
                        notificacao__aprendizagem=self,
                        notificacao__tipo=NotificacaoAprendizagem.NOTIFICACAO_RELATORIO_MONITOR,
                        notificacao__data__date__gte=datetime.date.today() + relativedelta(days=-10),
                    ).exists()
                )
            ):
                url_servidor = Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')
                titulo = '[SUAP] Pendência de Avaliação de Aprendiz sob sua Monitoria'
                assunto = (
                    '<h1>Pendência de Avaliação de Aprendiz sob sua Monitoria</h1>'
                    '<p>Prezado(a) monitor(a), solicitamos que cadastre em nosso sistema o Relatório de Atividades de Aprendizagem '
                    ' de {}.</p>'
                    '</p>Esta notificação se refere ao {}, e este relatório pode ser enviado a partir do dia {}.</p>'
                    '<p>Informamos que o relatório deve ser preenchido em formulário próprio para o empregado monitor disponível no link: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/aprendizagem/formularios/</p>'
                    '<p>Para registrar o relatório, acesse o link a seguir: '
                    '<a href="{}estagios/avaliar_aprendizagem_monitor/?matricula='
                    '{}&codigo_verificador={}&email_monitor={}&inicio={}&fim={}">Preencher Relatório de Atividades de Aprendizagem</a>.</p>'
                    '<p>Agradecemos a sua contribuição na formação do nosso aluno.</p>'.format(
                        self.aprendiz,
                        modulo,
                        format_(modulo.fim + datetime.timedelta(1)),
                        url_servidor,
                        self.aprendiz.matricula,
                        self.codigo_verificador[0:6],
                        self.email_monitor,
                        format_(modulo.inicio),
                        format_(modulo.fim),
                    )
                )
                send_mail(titulo, assunto, settings.DEFAULT_FROM_EMAIL, [self.email_monitor])
                notificacao = NotificacaoAprendizagem(
                    aprendizagem=self,
                    data=datetime.datetime.now(),
                    tipo=NotificacaoAprendizagem.NOTIFICACAO_RELATORIO_MONITOR,
                    notificador=user,
                    email_destinatario=self.email_monitor,
                    mensagem_enviada='{}<br/>{}'.format(titulo, assunto),
                )
                notificacao.save()
                modulo_notificado = ModuloComPendenciaNotificado(modulo=modulo, notificacao=notificacao)
                modulo_notificado.save()

    def notificar_pendencia_avaliacao_modulo_aprendiz(self, deve_notificar_se_pendente=False, user=None):
        hoje = datetime.date.today()
        for modulo in self.moduloaprendizagem_set.all():
            if (
                not modulo.tem_relatorio_aprendiz()
                and modulo.fim < hoje
                and (
                    deve_notificar_se_pendente
                    or not ModuloComPendenciaNotificado.objects.filter(
                        modulo=modulo,
                        notificacao__aprendizagem=self,
                        notificacao__tipo=NotificacaoAprendizagem.NOTIFICACAO_RELATORIO_APRENDIZ,
                        notificacao__data__date__gte=datetime.date.today() + relativedelta(days=-10),
                    ).exists()
                )
            ):
                url_servidor = Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')
                titulo = '[SUAP] Pendência de Envio de Relatório de Atividades de Aprendizagem'
                assunto = (
                    '<h1>Pendência de Envio de Relatório de Atividades de Aprendizagem</h1>'
                    '<p>Prezado(a) aprendiz(a), solicitamos que registre no SUAP o seu Relatório de Atividades de Aprendizagem.</p>'
                    '<p>Esta notificação se refere ao {}, e este relatório pode ser enviado a partir do dia {}.</p>'
                    '<p>Informamos que o relatório deve ser preenchido em formulário próprio, e assinado pelo(a) orientador(a) e supervisor(a) de estágio. O modelo encontra-se disponível no link: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/aprendizagem/formularios/</p>'
                    '<p>Para registrar o relatório, acesse o link a seguir: '
                    '<a href="{}accounts/login/?next=/estagios/aprendizagem/{}/?tab=relatorios">Relatórios</a>.</p>'
                    '<p>Em caso de dúvidas, procure a Coordenação responsável por estágios no seu Campus.</p>'.format(
                        modulo, format_(modulo.fim + datetime.timedelta(1)), url_servidor, self.pk
                    )
                )

                send_notification(titulo, assunto, settings.DEFAULT_FROM_EMAIL, [self.aprendiz.get_vinculo()])
                notificacao = NotificacaoAprendizagem(
                    aprendizagem=self,
                    data=datetime.datetime.now(),
                    tipo=NotificacaoAprendizagem.NOTIFICACAO_RELATORIO_APRENDIZ,
                    notificador=user,
                    email_destinatario=self.get_email_aprendiz(),
                    mensagem_enviada='{}<br/>{}'.format(titulo, assunto),
                )
                notificacao.save()
                modulo_notificado = ModuloComPendenciaNotificado(modulo=modulo, notificacao=notificacao)
                modulo_notificado.save()

    def pode_cadastrar_relatorio_aprendiz(self, user):
        return user == self.aprendiz.pessoa_fisica.user or in_group(
            user, 'Coordenador de Estágio, Coordenador de Estágio Sistêmico, estagios Administrador'
        )

    def pode_cadastrar_relatorio_monitor(self, user):
        return in_group(user, 'Coordenador de Estágio, Coordenador de Estágio Sistêmico, estagios Administrador')

    def get_data_inicio(self):
        if self.modulo_1:
            retorno = self.moduloaprendizagem_set.get(tipo_modulo=ModuloAprendizagem.MODULO_I).inicio
        elif self.modulo_2:
            retorno = self.moduloaprendizagem_set.get(tipo_modulo=ModuloAprendizagem.MODULO_II).inicio
        elif self.modulo_3:
            retorno = self.moduloaprendizagem_set.get(tipo_modulo=ModuloAprendizagem.MODULO_III).inicio
        elif self.modulo_4:
            retorno = self.moduloaprendizagem_set.get(tipo_modulo=ModuloAprendizagem.MODULO_IV).inicio
        else:
            retorno = None
        return retorno

    def get_data_prevista_encerramento(self):
        if self.modulo_4:
            retorno = self.moduloaprendizagem_set.get(tipo_modulo=ModuloAprendizagem.MODULO_IV).fim
        elif self.modulo_3:
            retorno = self.moduloaprendizagem_set.get(tipo_modulo=ModuloAprendizagem.MODULO_III).fim
        elif self.modulo_2:
            retorno = self.moduloaprendizagem_set.get(tipo_modulo=ModuloAprendizagem.MODULO_II).fim
        elif self.modulo_1:
            retorno = self.moduloaprendizagem_set.get(tipo_modulo=ModuloAprendizagem.MODULO_I).fim
        else:
            retorno = None
        return retorno

    def get_aditivo(self):
        lista = ['<ul>']
        for aditivo in self.aditivocontratualaprendizagem_set.all():
            lista.append('<li>{}</li>'.format(aditivo))
        lista.append('</ul>')
        return mark_safe(''.join(lista))

    get_aditivo.short_description = 'Aditivos Contratuais'

    def get_modulo_1(self):
        if self.moduloaprendizagem_set.filter(tipo_modulo=ModuloAprendizagem.MODULO_I).exists():
            return self.moduloaprendizagem_set.get(tipo_modulo=ModuloAprendizagem.MODULO_I)
        else:
            return None

    def get_modulo_2(self):
        if self.moduloaprendizagem_set.filter(tipo_modulo=ModuloAprendizagem.MODULO_II).exists():
            return self.moduloaprendizagem_set.get(tipo_modulo=ModuloAprendizagem.MODULO_II)
        else:
            return None

    def get_modulo_3(self):
        if self.moduloaprendizagem_set.filter(tipo_modulo=ModuloAprendizagem.MODULO_III).exists():
            return self.moduloaprendizagem_set.get(tipo_modulo=ModuloAprendizagem.MODULO_III)
        else:
            return None

    def get_modulo_4(self):
        if self.moduloaprendizagem_set.filter(tipo_modulo=ModuloAprendizagem.MODULO_IV).exists():
            return self.moduloaprendizagem_set.get(tipo_modulo=ModuloAprendizagem.MODULO_IV)
        else:
            return None

    def get_media_notas_avaliacoes_empregado_monitor(self):
        return RelatorioModuloAprendizagem.objects.filter(modulo_aprendizagem__aprendizagem=self, eh_relatorio_do_empregado_monitor=True).aggregate(Avg('nota_aprendiz'))[
            'nota_aprendiz__avg'
        ]

    def get_periodo_duracao(self):
        if self.data_encerramento:
            return [self.get_data_inicio(), self.data_encerramento]
        else:
            return [self.get_data_inicio(), self.get_data_prevista_encerramento()]

    def mostrar_botao_cancelar_encerramento(self):
        return (
            self.data_encerramento
            and not SolicitacaoCancelamentoEncerramentoEstagio.objects.filter(aprendizagem=self, situacao=SolicitacaoCancelamentoEncerramentoEstagio.AGUARDANDO_RESPOSTA).exists()
        )

    def ha_solicitacao_cancelamento_encerramento_aguardando_resposta(self):
        return SolicitacaoCancelamentoEncerramentoEstagio.objects.filter(aprendizagem=self, situacao=SolicitacaoCancelamentoEncerramentoEstagio.AGUARDANDO_RESPOSTA).exists()

    def verificar_matricula_irregular(self):
        # se ocorreu matrícula irregular por parte de um aluno
        if self.aprendiz.situacao in get_situacoes_irregulares() and not self.prazo_final_regularizacao_matricula_irregular:
            self.prazo_final_regularizacao_matricula_irregular = datetime.date.today() + relativedelta(days=7)
            self.save()
            self.notificar_empregado_monitor_matricula_irregular()
            self.notificar_aluno_matricula_irregular()
            self.notificar_orientador_aluno_matricula_irregular()
            self.notificar_coordenador_aluno_matricula_irregular()
            self.notificar_coordenacao_extensao_aluno_matricula_irregular()
        # se foi dado prazo e o aluno regularizou a matrícula
        if self.aprendiz.situacao not in get_situacoes_irregulares() and self.prazo_final_regularizacao_matricula_irregular:
            self.prazo_final_regularizacao_matricula_irregular = None
            self.save()
            self.notificar_empregado_monitor_matricula_regularizada()
        # se a situacao irregular persistiu por mais de 7 dias
        if (
            self.aprendiz.situacao in get_situacoes_irregulares()
            and self.prazo_final_regularizacao_matricula_irregular
            and self.prazo_final_regularizacao_matricula_irregular < datetime.date.today()
            and not self.notificacaoaprendizagem_set.filter(tipo=NotificacaoAprendizagem.NOTIFICACAO_INTERRUPCAO).exists()
        ):
            self.notificar_aluno_interrupcao()
            self.notificar_empregado_monitor_sobre_interrupcao_aprendizagem()
            self.notificar_orientador_interrupcao()

    def notificar_aluno_matricula_irregular(self):
        instituicao_sigla = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
        titulo = '[SUAP] Notificação de Matrícula Irregular'
        mensagem = (
            '<p>Caro(a), {}, sua matrícula no curso {},  encontra-se com a seguinte situação irregular: <strong>{}</strong>. '
            'Verificamos que você possui um contrato de aprendizagem '
            'com duração prevista até {}. A matricula e a frequência regulares são pré-requisitos para a manutenção deste contrato.</p>'
            '<p>É necessário que você procure o {} (Secretaria Acadêmica e Setor de '
            'Estágios/Extensão) para regularizar sua situação até o dia {}.</p>'
            '<p>Caso contrário, informaremos a empresa para que tome a providências legais cabíveis.</p>'.format(
                self.aprendiz,
                self.aprendiz.curso_campus,
                self.aprendiz.situacao.descricao,
                format_(self.get_data_prevista_encerramento()),
                instituicao_sigla,
                format_(self.prazo_final_regularizacao_matricula_irregular),
            )
        )

        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.aprendiz.get_vinculo()])
        email_aluno = self.get_email_aprendiz()
        if email_aluno:
            notificao = NotificacaoAprendizagem(
                aprendizagem=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAprendizagem.NOTIFICACAO_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=email_aluno,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_empregado_monitor_matricula_irregular(self):
        coordenadores = get_coordenadores_estagio(self.aprendiz)
        coordenadores_emails = get_coordenadores_emails(coordenadores)
        titulo = 'Notificação de Matrícula Irregular'
        mensagem = (
            '<p>Caro (a), {}, informamos que o (a) Aprendiz {} que se encontra sob sua supervisão, '
            'está com a matrícula em situação irregular: <strong>{}</strong>. O(a) aluno(a) tem até o dia {} para '
            'regularizar sua matrícula junto a nossa instituição. Após o prazo estabelecido, informaremos '
            'sobre a situação do (a) estudante em nossa instituição.</p>'
            '<p>Lembramos que se o aprendiz estiver com frequência no local de trabalho, e não comprovar '
            'a regularidade de sua matrícula junto a empresa, será caracterizado <strong>vínculo empregatício</strong>, '
            'conforme decreto 9.579/2018.</p>'
            '<p>Caso o estudante ou a empresa tenha realizado a rescisão, pedimos que a '
            'comprovação da rescisão na carteira de trabalho seja encaminhada para o(s) e-mail(s): {}. </p>'.format(
                self.nome_monitor, self.aprendiz, self.aprendiz.situacao.descricao, format_(self.prazo_final_regularizacao_matricula_irregular), coordenadores_emails
            )
        )
        email_monitor = self.email_monitor
        if email_monitor:
            send_mail(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [email_monitor])
            notificao = NotificacaoAprendizagem(
                aprendizagem=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAprendizagem.NOTIFICACAO_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=email_monitor,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_empregado_monitor_matricula_regularizada(self):
        titulo = 'Notificação de Matrícula Regularizada'
        mensagem = (
            '<p>Caro (a), {}, informamos que o(a) Aprendiz {} que se encontra sob sua supervisão, está '
            'com a matrícula em situação regular: <strong>{}</strong>. Desta forma, o contrato de '
            'aprendizagem pode seguir o prazo previamente estabelecido, até o dia: {} (data final do último módulo). </p>'
            '<p>Agradecemos a parceria no trabalho desempenhado.</p>'.format(
                self.nome_monitor, self.aprendiz, self.aprendiz.situacao.descricao, format_(self.get_data_prevista_encerramento())
            )
        )
        email_monitor = self.email_monitor
        if email_monitor:
            send_mail(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [email_monitor])
            notificao = NotificacaoAprendizagem(
                aprendizagem=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAprendizagem.NOTIFICACAO_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=email_monitor,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_coordenador_aluno_matricula_irregular(self):
        titulo = '[SUAP] Notificação de Aluno de Curso sob sua Coordenação com Matrícula Irregular'
        mensagem = (
            '<p>Caro(a), {}, informamos que o(a) estudante {}, tem um cadastro de aprendizagem '
            'em aberto e está com a seguinte situação irregular: <strong>{}</strong>. '
            'O(a) aluno(a) tem até o dia {} para regularizar sua matrícula junto a nossa instituição.</p>'
            '<p>Informamos que se o aprendiz estiver com frequência no local de trabalho, e não comprovar '
            'a regularidade de sua matrícula junto a empresa, será caracterizado vínculo empregatício, '
            'conforme decreto 9.579/2018. Caso o (a) aluno (a) não regularize sua '
            'situação, a empresa será notificada para que tome as providências legais cabíveis.</p>'
            '<p>É importante averiguar a situação em que se encontra o(a) estudante e entrar em contato com '
            'a Coordenação de Estágios/Extensão do Campus.</p>'.format(
                self.aprendiz.curso_campus.coordenador.nome, self.aprendiz, self.aprendiz.situacao.descricao, format_(self.prazo_final_regularizacao_matricula_irregular)
            )
        )
        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.aprendiz.curso_campus.coordenador.get_vinculo()])
        if self.aprendiz.curso_campus.coordenador.user.email:
            notificao = NotificacaoAprendizagem(
                aprendizagem=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAprendizagem.NOTIFICACAO_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=self.aprendiz.curso_campus.coordenador.user.email,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_orientador_aluno_matricula_irregular(self):
        titulo = '[SUAP] Notificação de Orientando com Matrícula Irregular'
        mensagem = (
            '<p>Caro(a), {}, informamos que o(a) estudante {}, tem um cadastro de aprendizagem '
            'em aberto, sob sua orientação, e está com a seguinte situação irregular: <strong>{}</strong>. '
            'O(a) aluno(a) tem até o dia {} para regularizar sua matrícula junto a nossa instituição.</p>'
            '<p>Informamos que o encerramento desse cadastro é importante para a contabilização da carga '
            'horária de prática profissional. Caso o (a) aluno (a) não regularize sua situação, o cadastro '
            'será interrompido por motivo de matrícula irregular.</p>'
            '<p>É importante averiguar a situação em que se encontra o(a) estudante e entrar em contato com '
            'a Coordenação de Estágios/Extensão do Campus.</p>'.format(
                self.orientador.vinculo.pessoa.nome, self.aprendiz, self.aprendiz.situacao.descricao, format_(self.prazo_final_regularizacao_matricula_irregular)
            )
        )
        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
        if self.orientador.vinculo.user.email:
            notificao = NotificacaoAprendizagem(
                aprendizagem=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAprendizagem.NOTIFICACAO_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=self.orientador.vinculo.user.email,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_coordenacao_extensao_aluno_matricula_irregular(self):
        coordenadores = get_coordenadores_estagio(self.aprendiz)
        coordenadores_nomes = get_coordenadores_nomes(coordenadores)
        coordenadores_emails = get_coordenadores_emails(coordenadores)
        coordenadores_vinculos = get_coordenadores_vinculos(coordenadores)
        titulo = '[SUAP] Notificação de Aprendizagem com Matrícula Irregular'
        instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
        mensagem = (
            '<p>Caros(as), Coordenadores(as) de Estágio {}, informamos que o(a) estudante {}, tem um cadastro de '
            'aprendizagem em aberto e está com a seguinte situação de matrícula irregular: <strong>{}</strong>. '
            'O(a) aluno(a) tem até o dia {} para regularizar sua matrícula junto ao {}.</p>'
            '<p>Lembramos que se o aprendiz estiver com frequência no local de trabalho, e não comprovar '
            'a regularidade de sua matrícula junto a empresa, será caracterizado <strong>vínculo empregatício</strong>, '
            'conforme decreto 9.579/2018. A pós o prazo estabelecido a situação '
            'de matrícula do(a) aluno(a) deve ser informada a empresa.</p>'
            'É importante averiguar a situação em que se encontra o(a) estudante para evitar '
            'possíveis prejuízos no relacionamento da empresa com o {} e nosso(a) aluno(a).'.format(
                coordenadores_nomes, self.aprendiz, self.aprendiz.situacao.descricao, format_(self.prazo_final_regularizacao_matricula_irregular), instituicao, instituicao
            )
        )
        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, coordenadores_vinculos)
        if coordenadores_emails:
            notificao = NotificacaoAprendizagem(
                aprendizagem=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAprendizagem.NOTIFICACAO_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=coordenadores_emails,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def get_data_envio_notificacao(self):
        return self.prazo_final_regularizacao_matricula_irregular + relativedelta(days=-7)

    def notificar_aluno_interrupcao(self):
        titulo = '[SUAP] Notificação de Rescisão/Encerramento de Aprendizagem'
        data_envio_notificacao = self.get_data_envio_notificacao()
        mensagem = (
            '<p>Caro(a), {}, de acordo com aviso enviado no dia {}, e diante da ausência de manifestação de '
            'sua parte, informamos que a empresa foi informada a respeito da situação e deve tomar as '
            'providências legais cabíveis.</p>'.format(self.aprendiz, format_(data_envio_notificacao))
        )

        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.aprendiz.get_vinculo()])
        email_aluno = self.get_email_aprendiz()
        if email_aluno:
            notificao = NotificacaoAprendizagem(
                aprendizagem=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAprendizagem.NOTIFICACAO_INTERRUPCAO,
                notificador=None,
                email_destinatario=email_aluno,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_orientador_interrupcao(self):
        titulo = '[SUAP] Notificação de Interrupção de Aprendizagem'
        mensagem = (
            '<p>Caro(a), {}, informamos que o(a) aprendiz {}, o qual se encontra sob sua orientação, '
            'não se manifestou a respeito da condição irregular de sua matrícula: <strong>{}</strong>. '
            'Desta forma, a empresa foi informada da situação e deve proceder a rescisão do contrato '
            'de aprendizagem.</p>'
            '<p>Além disso, é necessário averiguar a situação da prática profissional do(a) estudante, '
            'contabilizando as horas cumpridas, e se cabível, verificando a existência ou não de um '
            'relatório de prática profissional.</p>'.format(self.orientador.vinculo.pessoa.nome, self.aprendiz, self.aprendiz.situacao.descricao)
        )
        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
        if self.orientador.vinculo.user.email:
            notificao = NotificacaoAprendizagem(
                aprendizagem=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAprendizagem.NOTIFICACAO_INTERRUPCAO,
                notificador=None,
                email_destinatario=self.orientador.vinculo.user.email,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_empregado_monitor_sobre_interrupcao_aprendizagem(self):
        coordenadores = get_coordenadores_estagio(self.aprendiz)
        coordenadores_emails = get_coordenadores_emails(coordenadores)
        titulo = 'Notificação de Aprendiz com Matrícula Irregular'
        mensagem = (
            '<p>Caro(a), {}, informamos que o(a) Aprendiz {} que se encontra sob sua supervisão, '
            'não se manifestou a respeito da condição irregular de sua matrícula: <strong>{}</strong>, '
            'desta forma é necessário que seja feito o encerramento/rescisão, com a devida '
            'anotação na carteira de trabalho.</p>'
            '<p>Lembramos que se o aprendiz estiver com frequência no local de trabalho, e não comprovar '
            'a regularidade de sua matrícula junto a empresa, será caracterizado <strong>vínculo empregatício</strong>, '
            'conforme decreto 9.579/2018.</p>'
            '<p>Desta forma, pedimos que a comprovação da rescisão na certeira de trabalho seja encaminhada '
            'para o(s) e-mail(s): {}. </p>'.format(self.nome_monitor, self.aprendiz, self.aprendiz.situacao.descricao, coordenadores_emails)
        )
        email_monitor = self.email_monitor
        if email_monitor:
            send_mail(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [email_monitor])
            notificao = NotificacaoAprendizagem(
                aprendizagem=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAprendizagem.NOTIFICACAO_INTERRUPCAO,
                notificador=None,
                email_destinatario=email_monitor,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def verificar_envio_relatorio_frequencia(self):
        if self.periodicidade_envio_relatorio_frequencia:
            ultimo_periodo_frequencia = self.transformar_em_datas_passadas(self.ultimo_periodo_frequencia())
            inicio = ultimo_periodo_frequencia[0]
            fim = ultimo_periodo_frequencia[1]
            if not self.ha_relatorio_frequencia_ultimo_periodo_frequencia(inicio, fim):
                self.enviar_relatorio_frequencia(inicio, fim)

    def transformar_em_datas_passadas(self, periodo):
        hoje = datetime.date.today()
        inicio = periodo[0]
        fim = periodo[1]
        dia_hoje = hoje.day
        if dia_hoje > fim:
            data_fim = datetime.date(hoje.year, hoje.month, fim)
        else:
            hoje_menos_um_mes = hoje + relativedelta(months=-1)
            ultimo_dia = calendar.monthrange(hoje_menos_um_mes.year, hoje_menos_um_mes.month)[1]
            if fim > ultimo_dia:
                data_fim = datetime.date(hoje_menos_um_mes.year, hoje_menos_um_mes.month, ultimo_dia)
            else:
                data_fim = datetime.date(hoje_menos_um_mes.year, hoje_menos_um_mes.month, fim)
        if dia_hoje > inicio and dia_hoje > fim:
            data_inicio = datetime.date(hoje.year, hoje.month, inicio)
        elif fim > inicio:
            data_inicio = datetime.date(hoje.year, hoje.month, inicio) + relativedelta(months=-1)
        else:
            mes_desejado = data_fim.month - 1
            ano_desejado = hoje.year
            if data_fim.month == 1:
                mes_desejado = 12
                ano_desejado = hoje.year - 1
            data_inicio = datetime.date(ano_desejado, mes_desejado, calendar.monthrange(ano_desejado, mes_desejado)[1])
        if data_inicio.day != inicio:
            data_inicio = data_inicio + relativedelta(days=1)
        return [data_inicio, data_fim]

    def ultimo_periodo_frequencia(self):
        dia_hoje = datetime.date.today().day
        if self.periodicidade_envio_relatorio_frequencia == self.MENSAL:
            # Campos definidos no modelo de Aprendizagem
            return [self.inicio_periodo_frequencia_1, self.fim_periodo_frequencia_1]
        else:
            if self.distancia_em_dias(self.fim_periodo_frequencia_1, dia_hoje) < self.distancia_em_dias(self.fim_periodo_frequencia_2, dia_hoje):
                return [self.inicio_periodo_frequencia_1, self.fim_periodo_frequencia_1]
            else:
                return [self.inicio_periodo_frequencia_2, self.fim_periodo_frequencia_2]

    def distancia_em_dias(self, dia_anterior, dia_atual):
        if dia_atual == dia_anterior:
            return 31
        elif dia_atual > dia_anterior:
            return dia_atual - dia_anterior
        else:
            return 31 - dia_anterior + dia_atual

    # def hoje_eh_dia_enviar_relatorio_frequendia(self):
    #    return datetime.date.today().day in self.dias_envio_relatorio_frequendia()

    def ha_relatorio_frequencia_ultimo_periodo_frequencia(self, inicio, fim):
        return RelatorioFrequenciaNotificacaoAprendizagem.objects.filter(notificacao_aprendizagem__aprendizagem=self, inicio=inicio, fim=fim).exists()

    # def dias_envio_relatorio_frequendia(self):
    #     dias = list()
    #     if self.periodicidade_envio_relatorio_frequencia == self.MENSAL:
    #         dias.append(self.fim_periodo_frequencia_1+1)
    #     elif self.periodicidade_envio_relatorio_frequencia == self.QUINZENAL:
    #         dias.append(self.fim_periodo_frequencia_1+1)
    #         dias.append(self.fim_periodo_frequencia_2+1)
    #     return dias

    def enviar_relatorio_frequencia(self, inicio, fim):
        aulas = Aula.objects.filter(professor_diario__diario__matriculadiario__matricula_periodo__aluno=self.aprendiz, data__gte=inicio, data__lte=fim, quantidade__gt=0)
        quantidade_aulas = aulas.aggregate(Sum('quantidade')).get('quantidade__sum') or 0
        if quantidade_aulas > 1:
            faltas = Falta.objects.filter(matricula_diario__matricula_periodo__aluno=self.aprendiz, aula__in=aulas, abono_faltas=None)
            datas = aulas.values_list('data', flat=True).distinct()
            linhas = ''
            for data in datas:
                quantidade_aula_data = aulas.filter(data=data).aggregate(Sum('quantidade')).get('quantidade__sum') or 0
                percentagem_aula_data = 100 * quantidade_aula_data / float(quantidade_aulas)
                quantidade_faltas = faltas.filter(aula__data=data).aggregate(Sum('quantidade')).get('quantidade__sum') or 0
                percentagem_falta_data = 100 * quantidade_faltas / float(quantidade_aulas)
                linha = '<tr><td>{}</td><td>{} %</td><td>{} %</td><td>{} %</td></tr>'.format(
                    format_(data), format_(percentagem_aula_data - percentagem_falta_data), format_(percentagem_falta_data), format_(percentagem_aula_data)
                )
                linhas += linha

            total_faltas = faltas.aggregate(Sum('quantidade')).get('quantidade__sum') or 0
            percentagem_total_faltas = 100 * total_faltas / float(quantidade_aulas)
            total_presencas_abonos = quantidade_aulas - total_faltas
            percentagem_presencas_abonos = 100 * total_presencas_abonos / float(quantidade_aulas)
            linhas += '<tr><td>de {} até {}</td><td>{} %</td><td>{} %</td><td>100 %</td></tr>'.format(
                format_(inicio), format_(fim), format_(percentagem_presencas_abonos), format_(percentagem_total_faltas)
            )
            titulo = 'Notificação de Relatório de Presença do Jovem Aprendiz {}'.format(self.aprendiz)
            mensagem = (
                '<h1>Estágios</h1>'
                '<h2>[SUAP] Relatório de Frequência do Jovem Aprendiz</h2>'
                '<p>Senhores(as) representantes da organização {}, '
                'segue o relatório de presença do jovem aprendiz {}, no período de {} até {}.</p>'
                '<table border="1">'
                '<thead>'
                '<tr><th>Data</th><th>Percentagem Presenças e Abonos</th><th>Percentagem de Faltas</th><th>Percentagem de Aulas no Dia</th></tr>'
                '</thead>'
                '<tbody>'
                '{}'
                ''
                '</tbody>'
                '</table>'
                '<p>Relatório gerado em {}, às {}.</p>'
                ''.format(self.empresa, self.aprendiz, format_(inicio), format_(fim), linhas, format_(datetime.date.today()), datetime.datetime.now().strftime("%H:%M:%S"))
            )
        elif quantidade_aulas == 0:
            titulo = 'Notificação de Relatório de Presença do Jovem Aprendiz {}'.format(self.aprendiz)
            mensagem = (
                '<h1>Estágios</h1>'
                '<h2>[SUAP] Relatório de Frequência do Jovem Aprendiz</h2>'
                '<p>Senhores(as) representantes da organização {}, '
                'segue o relatório de presença do jovem aprendiz {}, no período de {} até {}.</p>'
                '<p><strong>Não houve aulas neste período para o jovem aprendiz.</strong></p>'
                '<p>Relatório gerado em {}, às {}.</p>'
                ''.format(self.empresa, self.aprendiz, format_(inicio), format_(fim), format_(datetime.date.today()), datetime.datetime.now().strftime("%H:%M:%S"))
            )
        emails_relatorio_frequencia = self.emails_relatorio_frequencia.split(',')
        if emails_relatorio_frequencia:
            send_mail(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, emails_relatorio_frequencia)
            notificao = NotificacaoAprendizagem(
                aprendizagem=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoAprendizagem.NOTIFICACAO_RELATORIO_FRENQUENCIA,
                notificador=None,
                email_destinatario=self.emails_relatorio_frequencia,
                mensagem_enviada='{}'.format(mensagem),
            )
            notificao.save()
            informacoes_relatorio = RelatorioFrequenciaNotificacaoAprendizagem(inicio=inicio, fim=fim, notificacao_aprendizagem=notificao)
            informacoes_relatorio.save()


class EnvioRelatorioFrequencia(models.ModelPlus):
    aprendizagem = models.ForeignKeyPlus(Aprendizagem)
    envio = models.DateFieldPlus('Data de Envio do Relatório')
    inicio_periodo = models.DateFieldPlus('Início do Período')
    fim_periodo = models.DateFieldPlus('Fim do Período')
    mensagem = models.TextField('Mensagem Enviada')
    emails = models.TextField('E-mails Recebedores')
    token = models.CharFieldPlus('Token')
    arquivo = models.FileFieldPlus(upload_to='estagios/relatorio_frequencia')


class ModuloAprendizagem(models.ModelPlus):
    MODULO_I = 1
    MODULO_II = 2
    MODULO_III = 3
    MODULO_IV = 4
    MODULO_CHOICES = [[MODULO_I, 'Módulo I'], [MODULO_II, 'Módulo II'], [MODULO_III, 'Módulo III'], [MODULO_IV, 'Módulo IV']]

    tipo_modulo = models.IntegerField('Tipo do Módulo', null=True, choices=MODULO_CHOICES)
    aprendizagem = models.ForeignKeyPlus(Aprendizagem, verbose_name='Aprendizagem')
    atividades = models.TextField('Descrição das Atividades do Módulo', help_text='Estas atividades serão utilizadas para as avaliações do módulo.')
    inicio = models.DateFieldPlus('Data de início do módulo')
    fim = models.DateFieldPlus('Data de fim do módulo')
    ch_teorica_semanal = models.IntegerField('Carga-Horária Teórica Semanal')
    ch_pratica_semanal = models.IntegerField('Carga-Horária Prática Semanal')

    def __str__(self):
        return '{} (de {} até {})'.format(self.get_tipo_modulo_display(), format_(self.inicio), format_(self.fim))

    def tem_relatorio_aprendiz(self):
        return self.relatoriomoduloaprendizagem_set.filter(eh_relatorio_do_empregado_monitor=False).exists()

    def tem_relatorio_monitor(self):
        return self.relatoriomoduloaprendizagem_set.filter(eh_relatorio_do_empregado_monitor=True).exists()

    def tem_visitas(self):
        return self.aprendizagem.visitaaprendizagem_set.filter(data_visita__range=(self.inicio, self.fim)).exists()

    @property
    def relatorio_aprendiz(self):
        if self.tem_relatorio_aprendiz():
            return self.relatoriomoduloaprendizagem_set.filter(eh_relatorio_do_empregado_monitor=False)[0]
        else:
            return None

    @property
    def relatorio_monitor(self):
        if self.tem_relatorio_monitor():
            return self.relatoriomoduloaprendizagem_set.filter(eh_relatorio_do_empregado_monitor=True)[0]
        else:
            return None

    @property
    def visitas(self):
        if self.visitaaprendizagem_set.exists():
            return self.aprendizagem.visitaaprendizagem_set.filter(data_visita__range=(self.inicio, self.fim))

    def ja_eh_tempo_de_cadastrar_relatorio(self, user):
        if user == self.aprendizagem.aprendiz.pessoa_fisica.user:
            return not self.aprendizagem.data_encerramento and self.fim < datetime.date.today()
        elif in_group(user, 'Coordenador de Estágio, Coordenador de Estágio Sistêmico'):
            return not self.aprendizagem.data_encerramento and self.inicio <= datetime.date.today()
        else:
            return False

    @property
    def foi_iniciado(self):
        return self.inicio <= datetime.date.today()

    @property
    def esta_encerrado(self):
        return self.fim < datetime.date.today()


class AditivoContratualAprendizagem(models.ModelPlus):
    aprendizagem = models.ForeignKeyPlus(Aprendizagem, verbose_name='Aprendizagem')
    tipos_aditivo = models.ManyToManyField('estagios.TipoAditivoAprendizagem', verbose_name='Tipos de Aditivo Contratual', blank=False)
    inicio_vigencia = models.DateFieldPlus('Início da Vigência', blank=False)
    aditivo = models.FileFieldPlus('Aditivo', blank=False, max_length=255, upload_to='aprendizagem/aditivo_aprendizagem')
    descricao = models.TextField('Descrição', null=True, blank=True)

    historico = models.TextField('Histórico', null=True)

    class Meta:
        verbose_name = 'Aditivo Contratual de Aprendizagem'
        verbose_name_plural = 'Aditivos Contratuais de Aprendizagem'

    def __str__(self):
        lista = []
        for tipo_aditivo in self.tipos_aditivo.all():
            lista.append(str(tipo_aditivo))
        return 'Descrição: {} <br>Tipos: {}'.format(self.descricao, ', '.join(lista))

    def save(self):
        super().save()
        self.aprendizagem.save()


class TipoAditivoAprendizagem(models.ModelPlus):
    # tipos de aditivo
    # são as próprias instâncias possíveis deste modelo
    # há apenas 1 instância por tipo de aditivo
    # o id de cada instância é o próprio valor da constante
    # veja o método 'popula_tipos_aditivos'
    PROFESSOR_ORIENTADOR = 1
    TEMPO = 2
    EMPREGADO_MONITOR = 3
    HORARIO = 4
    FILIAL = 5  # demanda 562

    TIPO_CHOICES = [[PROFESSOR_ORIENTADOR, 'Professor Orientador'], [TEMPO, 'Tempo'], [EMPREGADO_MONITOR, 'Empregado Monitor'], [HORARIO, 'Horário'], [FILIAL, 'Mudança de Filial']]

    descricao = models.CharFieldPlus('Decrição')

    class Meta:
        verbose_name = 'Tipo de Aditivo Contratual Aprendizagem'
        verbose_name_plural = 'Tipos de Aditivo Contratual Aprendizagem'

    @staticmethod
    def popula_tipos_aditivos():
        for tipo_aditivo in TipoAditivoAprendizagem.TIPO_CHOICES:
            tipo_aditivo_id = tipo_aditivo[0]
            tipo_aditivo_descricao = tipo_aditivo[1]
            # cria APENAS se não existir, pois este modelo é usado como FK
            TipoAditivoAprendizagem.objects.get_or_create(id=tipo_aditivo_id, descricao=tipo_aditivo_descricao)

    def __str__(self):
        return '{}'.format(self.descricao)


class VisitaAprendizagem(models.ModelPlus):
    aprendizagem = models.ForeignKeyPlus(Aprendizagem, verbose_name='Aprendizagem')
    modulo_aprendizagem = models.ForeignKeyPlus(ModuloAprendizagem, verbose_name='Módulo', default=None, null=True)
    orientador = models.ForeignKeyPlus(Professor, verbose_name='Orientador')

    # Dados Gerais
    data_visita = models.DateFieldPlus('Data da Visita')

    # Parecer da visita
    ambiente_adequado = models.BooleanField('Ambiente Adequado', default=False, help_text='O ambiente de trabalho está adequado ao desenvolvimento das ' 'atividades do aprendiz?')
    ambiente_adequado_justifique = models.TextField(
        'Justificativa para Ambiente Inadequado', default='', blank=True, help_text='Preencher somente em caso de resposta negativa ao ' 'quesito anterior.'
    )
    desenvolvendo_atividades_previstas = models.BooleanField(
        'Desenvolvimento Atividades Previstas', default=False, help_text='O aprendiz está desenvolvendo as atividades previstas no contrato de trabalho para este módulo?'
    )
    desenvolvendo_atividades_nao_previstas = models.BooleanField(
        'Desenvolvimento Atividades Não-Previstas',
        default=False,
        help_text='Existem atividades que estão sendo desenvolvidas (da competência do aprendiz), mas que não estão previstas no contrato de trabalho para este módulo?',
    )
    atividades_nao_previstas = models.TextField(
        'Atividades Não-Previstas',
        help_text='Se sim, descreva abaixo as atividades desenvolvidas que não foram previstas no plano de atividades, informando ao coordenador de estágios do campus do aluno a necessidade da sua atualização.',
        blank=True,
    )

    desenvolvendo_atividades_fora_competencia = models.BooleanField(
        'Desenvolvimento Atividades Fora da Competência', default=False, help_text='Existem atividades que estão sendo desenvolvidas fora das competências do aprendiz?'
    )

    apoiado_pelo_supervidor = models.BooleanField(
        'Apoiado pelo Supervisor', default=False, help_text='O aprendiz está sendo apoiado/orientado/supervisionado pelo empregado monitor desta aprendizagem na concedente?'
    )
    direitos_respeitados = models.BooleanField(
        'Direitos Respeitados', default=False, help_text='Os pagamentos mensais e demais benefícios, bem como o horário de trabalho estão sendo respeitados?'
    )
    direitos_respeitados_especificar = models.TextField(
        'Especificar direitos não respeitados', default='', blank=True, help_text='Preencher somente em caso de resposta negativa ao ' 'quesito anterior.'
    )
    aprendizagem_satisfatoria = models.BooleanField(
        'Aprendizagem Satisfatória',
        default=False,
        help_text='De um modo geral, quanto à contribuição ao aprendizado do aluno, as atividades estão ocorrendo de forma satisfatória?',
    )
    informacoes_adicionais = models.TextField(
        'Informações Adicionais',
        help_text='Espaço reservado ao registro de informações que considerar relevantes. (ex.: no caso alguma questão não tenha sido respondida, justificar; ou fazer o relato de outras informações colhidas durante a visita.)',
        blank=True,
    )
    relatorio = models.FileFieldPlus(
        'Relatório de Visita',
        help_text='Inserir o relatório de visita devidamente assinado. Limite de tamanho do arquivo 2MB.',
        blank=True,
        null=True,
        upload_to='visita_aprendizagem/relatorio',
        max_file_size=2097152,
    )
    ultimo_editor = models.ForeignKeyPlus('comum.User', verbose_name='Último Usuário a Editar', null=True)

    class Meta:
        verbose_name = 'Visita do Orientador'
        verbose_name_plural = 'Visitas do Orientador'

    def __str__(self):
        return 'Visita realizada em {}'.format(format_(self.data_visita))

    def save(self):
        self.modulo_aprendizagem = self.aprendizagem.moduloaprendizagem_set.filter(inicio__lte=self.data_visita, fim__gte=self.data_visita)[0]
        super().save()


class OrientacaoAprendizagem(models.ModelPlus):
    aprendizagem = models.ForeignKeyPlus(Aprendizagem, verbose_name='Aprendizagem')
    orientador = models.ForeignKeyPlus(Professor, verbose_name='Orientador')
    data = models.DateFieldPlus(verbose_name='Data da Reunião de Orientação')
    hora_inicio = models.TimeFieldPlus('Hora de Início')
    local = models.CharFieldPlus('Local')
    descricao = models.TextField('Descrição do Conteúdo da Orientação', blank=True, null=True)

    class Meta:
        ordering = ('-data',)

    def save(self, *args, **kwargs):
        url_servidor = Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')
        titulo = '[SUAP] Orientação de Aprendizagem Agendada'
        texto = (
            '<h1>Orientação de Aprendizagem Agendada</h1>'
            '<p>Foi agendada uma reunião de orientação ({}, {}, em {}) pelo seu orientador {} referente à '
            'aprendizagem em {}.</p>'
            '<p>Para mais detalhes acesse: '
            '<a href="{}accounts/login/?next=/estagios/aprendizagem/{}/?tab=reunioes">Reuniões</a>.</p>'.format(
                format_(self.data), self.hora_inicio, self.local, self.aprendizagem.orientador, self.aprendizagem.empresa, url_servidor, self.aprendizagem.pk
            )
        )

        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [self.aprendizagem.aprendiz.get_vinculo()])
        email_aprendiz = self.aprendizagem.get_email_aprendiz()
        if email_aprendiz:
            notificacao = NotificacaoAprendizagem(
                aprendizagem=self.aprendizagem,
                data=datetime.datetime.now(),
                tipo=NotificacaoAprendizagem.NOTIFICACAO_ORIENTACAO_APRENDIZAGEM,
                notificador=self.user,
                email_destinatario=email_aprendiz,
                mensagem_enviada='{}<br/>{}'.format(titulo, texto),
            )
            notificacao.save()
        super().save()


class RelatorioModuloAprendizagem(models.ModelPlus):
    AVALICAO_CONCEITO_EXCELENTE = 1
    AVALICAO_CONCEITO_BOM = 2
    AVALICAO_CONCEITO_REGULAR = 3
    AVALICAO_CONCEITO_RUIM = 4
    AVALICAO_CONCEITO_PESSIMO = 5
    AVALICAO_CONCEITO_CHOICES = [
        [AVALICAO_CONCEITO_EXCELENTE, 'Excelente'],
        [AVALICAO_CONCEITO_BOM, 'Bom'],
        [AVALICAO_CONCEITO_REGULAR, 'Regular'],
        [AVALICAO_CONCEITO_RUIM, 'Ruim'],
        [AVALICAO_CONCEITO_PESSIMO, 'Péssimo'],
    ]

    REALIZADA_SIM = 1
    REALIZADA_NAO = 2
    PARCIALMENTE_REALIZADA = 3
    REALIZADA_CHOICES = [[REALIZADA_SIM, 'Realizadas'], [REALIZADA_NAO, 'Não Realizadas'], [PARCIALMENTE_REALIZADA, 'Parcialmente Realizadas']]

    modulo_aprendizagem = models.ForeignKeyPlus(ModuloAprendizagem, verbose_name='Módulo da Aprendizagem')
    eh_relatorio_do_empregado_monitor = models.BooleanField(editable=False, default=True)

    # Dados gerais
    data_relatorio = models.DateFieldPlus('Data do Relatório', blank=False, null=True)

    # Atividades Previstas
    avaliacao_atividades = models.IntegerField('Sobre as Atividades', choices=REALIZADA_CHOICES)

    # Desenvolvimento das atividades
    comentarios_atividades = models.TextField(
        'Comentários sobre o desenvolvimento das atividades',
        null=True,
        blank=True,
        help_text='Descreva atividades que foram realizadas parcialmente ou que não foram realizadas e justifique.',
    )

    # Atividades não-previstas
    outras_atividades = models.TextField('Realizou atividades não previstas no resumo do curso? Informe e justifique', blank=True, null=True)

    # relação teoria/prática (somente relatório do aprendiz)
    aprendizagem_na_area_formacao = models.IntegerField(
        'Área de Formação', blank=False, null=True, help_text='A aprendizagem foi/está sendo desenvolvida em sua área ' 'de formação?', choices=[[1, 'Sim'], [0, 'Não']]
    )
    aprendizagem_contribuiu = models.IntegerField(
        'Contribuição da Aprendizagem', blank=False, null=True, help_text='As atividades desenvolvidas contribuíram para a sua ' 'formação?', choices=[[1, 'Sim'], [0, 'Não']]
    )
    aplicou_conhecimento = models.IntegerField(
        'Aplicação do Conhecimento',
        blank=False,
        null=True,
        help_text='Você teve oportunidade de aplicar os conhecimentos ' 'adquiridos no seu Curso?',
        choices=[[1, 'Sim'], [0, 'Não']],
    )

    # avaliação do aprendiz (somente relatório do aprendiz)
    avaliacao_conceito = models.IntegerField(
        'Conceito', help_text='Qual conceito você atribui ao desenvolvimento de suas atividades neste módulo?', choices=AVALICAO_CONCEITO_CHOICES, null=True, blank=False
    )

    avaliacao_comentarios = models.TextField(
        'Comentários e Sugestões',
        null=True,
        blank=True,
        help_text='Inserir comentário sobre o programa de aprendizagem em sua'
        ' empresa, ou sobre este módulo em especifico, e sua '
        'experiência recebendo o aprendiz. Se pertinente, deixe '
        'sugestões.',
    )

    # avaliação de desempenho do aprendiz(somente empregado monitor)
    nota_aprendiz = models.IntegerField(
        'Nota do Aprendiz',
        choices=[[nota, nota] for nota in range(10 + 1)],
        null=True,
        blank=False,
        help_text='Dê uma nota ao aprendiz que avalie seu desempenho como um todo de 0 a 10.',
    )

    # upload do arquivo do relatório
    relatorio = models.FileFieldPlus(
        'Relatório do Módulo',
        help_text='O relatório do módulo deve estar assinado pelo Aprendiz e pelo ' 'Empregado Monitor. Limite de tamanho do arquivo de 2MB.',
        blank=False,
        null=True,
        upload_to='relatorio_modulo_aprendizagem/relatorio',
        max_file_size=2097152,
    )

    ultimo_editor = models.ForeignKeyPlus('comum.User', verbose_name='Último Usuário a Editar', null=True)

    def __str__(self):
        return 'Relatório do Módulo ({})'.format(self.pk)

    def save(self):
        super().save()
        self.modulo_aprendizagem.aprendizagem.save()

    class Meta:
        verbose_name = 'Relatório de Atividades do Módulo da Aprendizagem'
        verbose_name_plural = 'Relatórios de Atividades dos Módulos da Aprendizagem'

    def can_delete(self, user=None):
        return not self.modulo_aprendizagem.aprendizagem.data_encerramento


class RelatorioFrequenciaNotificacaoAprendizagem(models.ModelPlus):
    inicio = models.DateFieldPlus('Início do Período de Apuração')
    fim = models.DateFieldPlus('Fim do Período de Apuração')
    notificacao_aprendizagem = models.ForeignKeyPlus('estagios.NotificacaoAprendizagem', verbose_name='Notificação')

    class Meta:
        verbose_name = 'Informações do Relatório de Frequência'
        verbose_name_plural = 'Informações do Relatório de Frequência'

    def __str__(self):
        return 'Informações do Relatório de Frequência ({})'.format(self.pk)


class NotificacaoAprendizagem(models.ModelPlus):
    NOTIFICACAO_INICIAL_PROFESSORES_DIARIOS = 1
    NOTIFICACAO_INICIAL = 2
    NOTIFICACAO_ORIENTACAO_APRENDIZAGEM = 3
    NOTIFICACAO_VISITA = 4
    NOTIFICACAO_RELATORIO_APRENDIZ = 5
    NOTIFICACAO_RELATORIO_MONITOR = 6
    NOTIFICACAO_MATRICULA_IRREGULAR = 7
    NOTIFICACAO_INTERRUPCAO = 8
    NOTIFICACAO_RELATORIO_FRENQUENCIA = 9

    TIPO_CHOICES = [
        [NOTIFICACAO_INICIAL_PROFESSORES_DIARIOS, 'Notificação inicial aos professores dos diários.'],
        [NOTIFICACAO_INICIAL, 'Notificação inicial.'],
        [NOTIFICACAO_ORIENTACAO_APRENDIZAGEM, 'Notificação de Orientação de Aprendizagem'],
        [NOTIFICACAO_VISITA, 'Notificação de Pendência de Visita'],
        [NOTIFICACAO_RELATORIO_APRENDIZ, 'Notificação de Pendência de Relatório de Avaliação pelo Aprendiz.'],
        [NOTIFICACAO_RELATORIO_MONITOR, 'Notificação de Pendência de Relatório de Avaliação pelo Empregado Monitor.'],
        [NOTIFICACAO_MATRICULA_IRREGULAR, 'Notificação de Matrícula Irregular do Aluno.'],
        [NOTIFICACAO_INTERRUPCAO, 'Notificação de Interrupção do Cadastro de Aprendizagem.'],
        [NOTIFICACAO_RELATORIO_FRENQUENCIA, 'Notificação de Relatório de Frequência.'],
    ]

    aprendizagem = models.ForeignKeyPlus(Aprendizagem, verbose_name='Aprendizagem')
    notificador = models.ForeignKeyPlus('comum.User', verbose_name='Notificador', null=True)
    data = models.DateTimeFieldPlus('Data da Notificação')
    tipo = models.IntegerField('Tipo', choices=TIPO_CHOICES)
    email_destinatario = models.TextField('E-mail')
    mensagem_enviada = models.TextField('Mensagem Enviada')

    class Meta:
        ordering = ('-data',)
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'

    def __str__(self):
        return '{}-{}'.format(self.pk, self.get_tipo_display())


class ModuloComPendenciaNotificado(models.ModelPlus):
    modulo = models.ForeignKeyPlus(ModuloAprendizagem, verbose_name='Módulo Aprendizagem')
    notificacao = models.ForeignKeyPlus(NotificacaoAprendizagem, verbose_name='Notificação')


class JustificativaVisitaModuloAprendizagem(models.ModelPlus):
    modulo = models.ForeignKeyPlus(ModuloAprendizagem, verbose_name='Módulo Aprendizagem')
    motivos = models.TextField('Informo que a visita à organização concedente não foi realizada pelos seguintes motivos', blank=False)
    outros_acompanhamentos = models.TextField('Foram realizadas outras formas de acompanhamento do (a) aluno (a) sob sua orientação? Se sim, informe quais', blank=True)
    formulario_justificativa = models.FileFieldPlus(
        'Formulário de Justificativa',
        help_text='Esse documento deve ser solicitado ao Coordenador de Estágios, preenchido pelo orientador, e assinado pelo (a) Aluno (a) e Coordenador de Curso/Diretor Acadêmico. Limite de tamanho do arquivo de 2MB',
        blank=False,
        upload_to='justificativa_visita_modulo_aprendizagem/relatorio',
        max_file_size=2097152,
    )


class TipoRemuneracao(models.ModelPlus):
    descricao = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = 'Tipos de Remuneração'
        verbose_name = 'Tipos de Remunerações'

    def __str__(self):
        return self.descricao


class SituacaoAtividade(models.ModelPlus):
    descricao = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = 'Situação de Atividade'
        verbose_name = 'Situações de Atividades'

    def __str__(self):
        return self.descricao


class OfertaPraticaProfissional(models.ModelPlus):
    ESTAGIO = 1
    JOVEM_APRENDIZ = 2

    TIPO_CHOICES = [[ESTAGIO, 'Estágio'], [JOVEM_APRENDIZ, 'Jovem Aprendiz']]

    # Dados Gerais
    concedente = models.CharFieldPlus('Concedente', default='')
    data_inicio = models.DateFieldPlus('Início das Inscrições')
    data_fim = models.DateFieldPlus('Fim das Inscrições')

    # Dados da Oferta
    tipo_oferta = models.PositiveIntegerFieldPlus('Tipo da Oferta', choices=TIPO_CHOICES, null=True, blank=False)
    cursos = models.ManyToManyFieldPlus(CursoCampus, verbose_name='Cursos', blank=False)
    a_partir_do_periodo = models.IntegerField('A Partir do Período', blank=True, null=True, choices=[[nota, nota] for nota in range(1, 10 + 1)])
    turno = models.ForeignKeyPlus(
        'edu.Turno',
        verbose_name='Alunos do Turno',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text='Não preencher caso a oferta seja direcionada a alunos de diversos turnos.',
    )
    qtd_vagas = models.IntegerField('Quantidade de Vagas')

    # Carga-Horária
    ch_semanal = models.IntegerField('C.H. Semanal')

    # Outras Informações
    folder = models.FileFieldPlus('Folder Publicitário', null=True, blank=True, max_length=255, upload_to='ofertas/folders')
    habilidades = models.TextField('Habilidades', blank=True)
    descricao_atividades = models.TextField('Descrição das Atividades', blank=True)
    observacoes = models.TextField('Observações', blank=True)

    class Meta:
        verbose_name = 'Oferta de Estágio ou Jovem Aprendiz'
        verbose_name_plural = 'Ofertas de Estágios ou Jovem Aprendiz'

    def __str__(self):
        return 'Oferta de Estágio ou Jovem Aprendiz na Concedente {} ({:d} vagas)'.format(self.concedente, self.qtd_vagas)

    def get_absolute_url(self):
        return '/estagios/oferta_pratica_profissional/{}/'.format(self.pk)


class PraticaProfissional(models.ModelPlus):
    TIPO_ESTAGIO = 1
    TIPO_ATIVIDADE_PROFISSIONAL = 2
    TIPO_APRENDIZAGEM = 3
    TIPO_CHOICES = [[TIPO_ESTAGIO, 'Estágio'], [TIPO_APRENDIZAGEM, 'Aprendizagem'], [TIPO_ATIVIDADE_PROFISSIONAL, 'Atividade Profissional Efetiva']]

    MOTIVO_CONCLUSAO = 1
    MOTIVO_RESCISAO = 2
    MOTIVO_RESCISAO_MATRICULA_IRREGULAR = 3
    MOTIVO_CHOICES = [[MOTIVO_CONCLUSAO, 'Conclusão'], [MOTIVO_RESCISAO, 'Rescisão']]

    MOTIVO_POR_TERMINO_PREVISTO = 1
    MOTIVO_CONTRATACAO = 2
    MOTIVO_RESCISAO_ESTAGIARIO = 3
    MOTIVO_RESCISAO_CONCEDENTE = 4
    MOTIVO_RESCISAO_INSTITUICAO = 5
    MOTIVACAO_DESLIGAMENTO_ENCERRAMENTO_CHOICHES = [
        [MOTIVO_POR_TERMINO_PREVISTO, 'Por término do período previsto no Termo de Compromisso.'],
        [MOTIVO_CONTRATACAO, 'Contratação do estagiário pela concedente.'],
        [MOTIVO_RESCISAO_ESTAGIARIO, 'Rescisão por iniciativa do estagiário.'],
        [MOTIVO_RESCISAO_CONCEDENTE, 'Rescisão por iniciativa da concedente.'],
        [MOTIVO_RESCISAO_INSTITUICAO, 'Rescisão por iniciativa da instituição de ensino.'],
    ]

    SITUACAO_APROVADO = 1
    SITUACAO_REPROVADO = 2
    SITUACAO_CHOICES = [[SITUACAO_APROVADO, 'Aprovado'], [SITUACAO_REPROVADO, 'Reprovado']]

    CONCEITO_EXCELENTE = 'Excelente'
    CONCEITO_MUITO_BOM = 'Muito Bom'
    CONCEITO_BOM = 'Bom'
    CONCEITO_REGULAR = 'Muito Regular'
    CONCEITO_INSUFICIENTE = 'Insuficiente'
    CONCEITO_CHOICES = [
        [CONCEITO_EXCELENTE, CONCEITO_EXCELENTE],
        [CONCEITO_MUITO_BOM, CONCEITO_MUITO_BOM],
        [CONCEITO_BOM, CONCEITO_BOM],
        [CONCEITO_REGULAR, CONCEITO_REGULAR],
        [CONCEITO_INSUFICIENTE, CONCEITO_INSUFICIENTE],
    ]

    STATUS_EM_ANDAMENTO = 1
    STATUS_COM_PENDENCIA = 2
    STATUS_APTO_PARA_CONCLUSAO = 5
    STATUS_AGUARDANDO_AVALIACAO_ESTAGIARIO = 3
    STATUS_CONCLUIDO = 6
    STATUS_RESCINDIDO = 7
    STATUS_CHOICES = [
        [STATUS_EM_ANDAMENTO, 'Em Andamento/Em Fase Inicial'],
        [STATUS_COM_PENDENCIA, 'Com Pendência'],
        [STATUS_APTO_PARA_CONCLUSAO, 'Apto para Encerramento'],
        [STATUS_CONCLUIDO, 'Encerrado'],
        [STATUS_RESCINDIDO, 'Rescindido'],
    ]

    # Dados Gerais
    tipo = models.IntegerField('Tipo', choices=TIPO_CHOICES, default=TIPO_ESTAGIO)
    obrigatorio = models.BooleanField('O estágio é obrigatório', choices=[[False, 'Estágio não-obrigatório'], [True, 'Estágio obrigatório']], blank=True, null=False)
    turno = models.ForeignKeyPlus(Turno, verbose_name='Turno', on_delete=models.CASCADE)
    aluno = models.ForeignKeyPlus(Aluno, verbose_name='Estagiário')
    convenio = models.ForeignKeyPlus(Convenio, verbose_name='Convênio', null=True, blank=True)
    empresa = models.ForeignKeyPlus(
        Pessoa,
        verbose_name='Concedente',
        help_text='Para adicionar um concedente de estágio pessoa jurídica acesse: '
        '<strong>Administração -> Cadastros -> Pessoas Júridicas</strong>. '
        'Se for pessoa física, acesse: <strong>Administração -> Cadastros -> '
        'Pessoas Externas</strong>.',
    )
    cidade = models.ForeignKeyPlus('edu.Cidade', verbose_name='Município', null=True, on_delete=models.CASCADE, blank=True)
    logradouro = models.CharFieldPlus(null=True, blank=True)
    numero = models.CharField('Nº', max_length=50, null=True, blank=True)
    complemento = models.CharFieldPlus(null=True, blank=True)
    bairro = models.CharFieldPlus(null=True, blank=True)
    cep = models.CharField('CEP', max_length=9, null=True, blank=True)
    representante_concedente = models.ForeignKeyPlus(
        'rh.PessoaFisica',
        null=True,
        verbose_name='Representante da Concedente',
        blank=True,
        on_delete=models.CASCADE,
        related_name='estagio_representante_concedente',
        help_text="Só preencher esse campo, se for utilizar a funcionalidade de Documento Eletrônico.",
    )
    nome_representante_concedente = models.CharFieldPlus(
        'Nome do Representante',
        blank=True,
        null=True,
        help_text='Representante da concedente que assinará o ' 'termo de compromisso' ". Não preencher esse campo, se for utilizar a funcionalidade de Documento Eletrônico.",
    )
    cargo_representante_concedente = models.CharFieldPlus('Cargo do Representante', blank=True, null=True)
    ramo_atividade = models.CharFieldPlus('Ramo de Atividade', blank=True, null=True)
    orientador = models.ForeignKeyPlus(Professor, verbose_name='Professor Orientador')
    servidor_representante = models.ForeignKeyPlus(
        Servidor,
        related_name='estagios_como_servidor_representante_set',
        verbose_name='Servidor Representante da Instituição de Ensino',
        null=True,
        blank=True,
        help_text='Servidor que assinará o Termo de Compromisso em nome ' 'da instituição de ensino.',
    )

    # Bolsa
    remunerada = models.BooleanField('Remunerada', default=False)
    tipo_remuneracao = models.ForeignKeyPlus(TipoRemuneracao, verbose_name='Tipo de Remuneração', null=True, blank=True, on_delete=models.CASCADE)
    valor = models.DecimalFieldPlus(verbose_name='Bolsa (R$)', null=True, blank=True)
    auxilio_transporte = models.DecimalFieldPlus(verbose_name='Auxílio Transporte (R$)', null=True, blank=True)
    auxilio_alimentacao = models.DecimalFieldPlus(verbose_name='Outros Benefícios (R$)', null=True, blank=True, help_text='Soma de outros benefícios.')
    descricao_outros_beneficios = models.TextField('Descrição', blank=True, help_text='Descrição de outros benefícios recebidos.')

    # Carga Horária
    data_inicio = models.DateFieldPlus('Data de Início')
    data_prevista_fim = models.DateFieldPlus('Data Prevista para Encerramento')
    ch_semanal = models.DecimalField('C.H. Semanal', decimal_places=1, max_digits=3)
    ch_diaria = models.DecimalField('C.H. Diária', decimal_places=1, max_digits=3, null=True, blank=True)
    horario = models.CharFieldPlus(
        'Horário do Estágio',
        help_text='Exemplos: "de segunda a sexta, das 7:30 às 11:30",'
        ' "segunda e quarta, das 7:00 às 12:00 e das 13:00 '
        'às 17:00 e sexta das 8:00 às 12:00". '
        'Esse texto será usado para o preenchimento do '
        'campo horário no Termo de Compromisso gerado pelo '
        'sistema.',
        null=True,
        blank=True,
    )

    # Documentação
    relatorio_avaliacao_instalacoes = models.PrivateFileField(
        'Relatório de avaliação das Instalações ',
        help_text="Relatório previsto no inciso II, artigo 7º, Lei nº 11.788.",
        blank=True,
        max_length=255,
        upload_to='pratica_profissional/relatorio_avaliacao_instalacoes',
    )

    plano_atividades = models.FileFieldPlus('Plano de Atividades', blank=True, max_length=255, upload_to='pratica_profissional/planos_atividades')
    termo_compromisso = models.FileFieldPlus(
        'Termo de Compromisso',
        blank=True,
        max_length=255,
        upload_to='pratica_profissional/termos_compromissos',
        help_text='Caso o documento seja unificado (contenha o Plano de Atividades e ' 'o Termo de Compromisso) inserir o arquivo duas vezes.',
    )
    termo_compromisso_documentotexto = models.ForeignKeyPlus(
        'documento_eletronico.DocumentoTexto', null=True, on_delete=models.PROTECT, verbose_name="Termo de Compromisso - Documento Eletrônico"
    )
    documentacao_comprobatoria = models.FileFieldPlus('Documentação Comprobatória', blank=True, max_length=255, upload_to='pratica_profissional/documentacao_comprobatoria')

    # Seguro
    nome_da_seguradora = models.CharFieldPlus('Nome da Seguradora', blank=False, null=True)
    cnpj_da_seguradora = models.BrCnpjField(verbose_name='CNPJ da Seguradora', null=True, blank=True)
    numero_seguro = models.CharFieldPlus('Número da Apólice do Seguro')

    # Supervisor
    nome_supervisor = models.CharFieldPlus('Nome', blank=False, help_text="Não preencher esse campo, se for utilizar a funcionalidade de Documento Eletrônico.")
    telefone_supervisor = models.CharFieldPlus('Telefone', blank=False)
    cargo_supervisor = models.CharFieldPlus('Cargo', blank=False)
    email_supervisor = models.CharFieldPlus('E-mail', blank=False, help_text='Este e-mail será importante para o envio da avaliação.')
    observacao = models.TextField('Observação', blank=True)
    supervisor = models.ForeignKeyPlus(
        'rh.PessoaFisica',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='estagio_supervisor',
        help_text="Só preencher esse campo, se for utilizar a funcionalidade de Documento Eletrônico.",
    )

    # Dados de Encerramento
    data_fim = models.DateFieldPlus('Data do Encerramento', null=True)
    movito_encerramento = models.IntegerField('Encerramento por', null=True, choices=MOTIVO_CHOICES)
    motivacao_desligamento_encerramento = models.IntegerField('Motivação do Desligamento/ Encerramento', null=True, choices=MOTIVACAO_DESLIGAMENTO_ENCERRAMENTO_CHOICHES)
    motivo_rescisao = models.TextField(
        'Observações', null=True, blank=True, help_text='Inserir o motivo da rescisão, do encerramento com pendência ou outras informações relevantes.'
    )
    situacao = models.IntegerField('Situação', null=True, blank=True, choices=SITUACAO_CHOICES)
    ch_final = models.IntegerField('C.H. Final', default=0)
    ficha_frequencia = models.FileFieldPlus('Ficha de Frequência', null=True, blank=True, max_length=255, upload_to='pratica_profissional/ficha_frequencia')
    termo_encerramento = models.FileFieldPlus('Termo de Realização de Estágio', null=True, blank=False, max_length=255, upload_to='pratica_profissional/termos_encerramento')
    estagio_anterior_20161 = models.BooleanField(
        'Estágio anterior a 2017.1',
        help_text='Marcar "Sim" caso este estágio não tenha toda a documentação necessária para encerramento e tenha se encerrado até o dia 30/04/2017 (Anterior ao início do ano letivo 2017.1).',
        default=False,
        choices=[[True, 'Sim'], [False, 'Não']],
    )

    # Avaliacao do Estagiário
    data_avaliacao_aluno = models.DateField('Data da Avaliação', null=True)
    contribuiu_formacao = models.BooleanField('Contribuiu para Formação', help_text='As atividades desenvolvidas contribuiram para a sua formação ' 'profissional?', default=False)
    aplicou_conhecimentos = models.BooleanField('Aplicou Conhecimentos', help_text='Você teve oportunidade de aplicar conhecimentos adquiridos ' 'no seu curso?', default=False)
    conceito = models.CharFieldPlus('Conceito', choices=CONCEITO_CHOICES, help_text='Qual conceito você atribui ao seu estágio?', default='')
    comentarios = models.TextField(
        'Comentários e Sugestões',
        null=True,
        blank=True,
        help_text='Aqui você pode falar sobre sua experiência de estágio, aprendizado, ' 'atividades desenvolvidas na concedente e dar sugestões.',
    )

    # Avaliação do Supervisor
    avaliacao_supervisor = models.FileFieldPlus(
        'Avaliação do Supervisor',
        null=True,
        blank=False,
        max_length=255,
        upload_to='pratica_profissional/avaliacao_supervisor',
        help_text='Esta deve ser a versão original assinada pelo Supervisor',
    )
    data_avaliacao_supervisor = models.DateField('Data da Avaliação', null=True)
    atividades_nao_previstas = models.TextField('Atividades Não-Previstas', blank=True, default='')
    comentarios_supervisor = models.TextField(
        'Comentários do Supervisor',
        null=True,
        blank=False,
        help_text='Aqui o supervisor pode falar sobre a prática do estagiário ' 'em sua concedente e sua experiência recebendo o estagiário e ' 'dar sugestões.',
    )

    status = models.IntegerField('Situação', default=STATUS_EM_ANDAMENTO, choices=STATUS_CHOICES)
    data_atualizacao_situacao = models.DateField('Data da Atualização do Situação', null=True)
    pendente_visita = models.BooleanField('Pendente de Visita?', null=True, blank=True)
    pendente_relatorio_estagiario = models.BooleanField('Pendente de Relatório do Estagiário?', null=True, blank=True)
    pendente_relatorio_supervisor = models.BooleanField('Pendente de Relatório do Supervisor?', null=True, blank=True)
    codigo_verificador = models.TextField(default='')

    # Prazo para regularizar a matrícula
    prazo_final_regularizacao_matricula_irregular = models.DateFieldPlus('Prazo Final para Regularizar a Matrícula', null=True, blank=True)
    desvinculado_matricula_irregular = models.BooleanField('Aluno Desvinculado por Matrícula Irregular', help_text='Selecione para o caso de abandono do aluno.', default=False)

    testemunha1 = models.ForeignKeyPlus(
        'rh.PessoaFisica',
        null=True,
        blank=True,
        verbose_name='Testemunha 1',
        on_delete=models.CASCADE,
        related_name='estagio_testemunha1',
        help_text="Só preencher esse campo, se for utilizar a funcionalidade de Documento Eletrônico.",
    )
    testemunha_1 = models.CharFieldPlus(
        'Nome da Testemunha 1',
        null=True,
        blank=True,
        help_text='Testemunha que assinará o termo de compromisso. Não preencher esse campo, se for utilizar a funcionalidade de Documento Eletrônico.',
    )
    testemunha2 = models.ForeignKeyPlus(
        'rh.PessoaFisica',
        null=True,
        blank=True,
        verbose_name='Testemunha 2',
        on_delete=models.CASCADE,
        related_name='estagio_testemunha2',
        help_text="Só preencher esse campo, se for utilizar a funcionalidade de Documento Eletrônico.",
    )
    testemunha_2 = models.CharFieldPlus(
        'Nome da Testemunha 2',
        null=True,
        blank=True,
        help_text='Testemunha que assinará o termo de compromisso. Não preencher esse campo, se for utilizar a funcionalidade de Documento Eletrônico.',
    )
    agente_integracao = models.ForeignKeyPlus(PessoaJuridica, verbose_name='Agente de Integração', null=True, blank=True, related_name='agentes_integracao')

    class History:
        ignore_fields = ('data_atualizacao_situacao',)

    class Meta:
        verbose_name = 'Estágio'
        verbose_name_plural = 'Estágios'

    @transaction.atomic()
    def save(self):
        """
        if self.movito_encerramento == self.MOTIVO_RESCISAO:
            self.status = PraticaProfissional.STATUS_RESCINDIDO
            self.notificar()
            super(PraticaProfissional, self).save()
            return

        if self.estagio_anterior_20161 is True:
            self.status = PraticaProfissional.STATUS_CONCLUIDO
            self.notificar()
            super(PraticaProfissional, self).save()
            return

        if somar_data(self.data_inicio, 90) > datetime.date.today():
            self.status = PraticaProfissional.STATUS_EM_ANDAMENTO
        else:
            if self.visitapraticaprofissional_set.exists():
                if self.data_avaliacao_supervisor:
                    if not self.data_avaliacao_aluno:
                        self.status = PraticaProfissional.STATUS_AGUARDANDO_AVALIACAO_ALUNO
                    else:
                        if self.data_fim:
                            self.status = PraticaProfissional.STATUS_CONCLUIDO
                        else:
                            self.status = PraticaProfissional.STATUS_APTO_PARA_CONCLUSAO
                else:
                    self.status = PraticaProfissional.STATUS_AGUARDANDO_RELATORIO_SUPERVISOR
            else:
                self.status = PraticaProfissional.STATUS_AGUARDANDO_VISITA_ORIENTADOR
        if not self.codigo_verificador:
            self.codigo_verificador = hashlib.sha1('{}{}{}'.format(
                self.orientador.pk, datetime.datetime.now(), settings.SECRET_KEY).encode()).hexdigest()
        super(PraticaProfissional, self).save()
        self.notificar()
        """
        self.data_atualizacao_situacao = None
        self.atualizar_situacoes()
        self.atualiza_status()
        if not self.codigo_verificador:
            self.codigo_verificador = hashlib.sha1('{}{}{}'.format(self.orientador.pk, datetime.datetime.now(), settings.SECRET_KEY).encode()).hexdigest()

        super().save()

    def ha_pendencia_de_visita(self, data_considerada=None):
        if not data_considerada:
            data_considerada = datetime.date.today()
        if self.data_fim:
            return False
        periodos_trimestrais = self.get_periodos_trimestrais()
        pendente_visita = False
        for periodo in periodos_trimestrais:
            if periodo['fim'] <= data_considerada:
                if (
                    not self.visitapraticaprofissional_set.filter(data_visita__range=(periodo['inicio'], periodo['fim'])).exists()
                    and not self.justificativavisitaestagio_set.filter(inicio=periodo['inicio'], fim=periodo['fim']).exists()
                ):
                    pendente_visita = True
                    break
        return pendente_visita

    def ha_pendencia_relatorio_supervisor(self, data_considerada=None):
        if not data_considerada:
            data_considerada = datetime.date.today()
        if self.data_fim:
            return False
        periodos_semestrais = self.get_periodos_semestrais()
        pendente_relatorio_supervisor = False
        for periodo in periodos_semestrais:
            if periodo['inicio'] + relativedelta(months=+3, days=-1) <= data_considerada:
                if not self.relatoriosemestralestagio_set.filter(eh_relatorio_do_supervisor=True, inicio=periodo['inicio'], fim=periodo['fim']).exists():
                    pendente_relatorio_supervisor = True
                    break
        return pendente_relatorio_supervisor

    def ha_pendencia_relatorio_estagiario(self, data_considerada=None):
        if not data_considerada:
            data_considerada = datetime.date.today()
        if self.data_fim:
            return False
        periodos_semestrais = self.get_periodos_semestrais()
        pendente_relatorio_estagiario = False
        for periodo in periodos_semestrais:
            if periodo['inicio'] + relativedelta(months=+3, days=-1) <= data_considerada:
                if not self.relatoriosemestralestagio_set.filter(eh_relatorio_do_supervisor=False, inicio=periodo['inicio'], fim=periodo['fim']).exists():
                    pendente_relatorio_estagiario = True
                    break
        return pendente_relatorio_estagiario

    def estah_no_prazo_para_envio_relatorio_estagiario(self, data_considerada=None):
        if not data_considerada:
            data_considerada = datetime.date.today()
        if self.data_fim:
            return False
        for periodo in self.get_periodos_semestrais():
            if periodo.get('fim') and periodo.get('fim') < data_considerada:
                return True
        return False

    def pode_registrar_relatorio_estagiario(self, user, exclude_relatorio_pk=None):
        if not in_group(user, ['Coordenador de Estágio', 'Coordenador de Estágio Sistêmico']) and not user == self.aluno.pessoa_fisica.user and not user.is_superuser:
            return False
        if self.estah_no_prazo_para_envio_relatorio_estagiario():
            for periodo in self.get_periodos_semestrais():
                if not self.relatoriosemestralestagio_set.filter(
                    eh_relatorio_do_supervisor=False, inicio=periodo['inicio'], fim=periodo['fim']
                ).exclude(pk=exclude_relatorio_pk).exists():
                    return True
        return False

    def atualizar_situacoes(self, salvar=False):
        if self.data_fim:
            tem_pendencia = self.pendente_relatorio_supervisor or self.pendente_relatorio_estagiario or self.pendente_visita
            if tem_pendencia:
                self.pendente_visita = False
                self.pendente_relatorio_estagiario = False
                self.pendente_relatorio_supervisor = False
                super().save()
            return
        else:
            self.pendente_visita = self.ha_pendencia_de_visita()
            self.pendente_relatorio_supervisor = self.ha_pendencia_relatorio_supervisor()
            self.pendente_relatorio_estagiario = self.ha_pendencia_relatorio_estagiario()
            self.data_atualizacao_situacao = datetime.date.today()
            if not self.pendente_relatorio_estagiario and not self.pendente_relatorio_supervisor and not self.pendente_visita and self.data_prevista_fim < datetime.date.today():
                self.notificar_apto_para_conclusao()
            if salvar:
                super().save()

    def resumo_pendencias(self):
        self.atualizar_situacoes(salvar=True)

        if self.data_fim:
            retorno = 'Encerrado'
            return mark_safe(retorno)

        pendencias = []
        if self.pendente_visita:
            pendencias.append('de visita do orientador')
        if self.pendente_relatorio_estagiario:
            pendencias.append('de relatório do estagiário')
        if self.pendente_relatorio_supervisor:
            pendencias.append('de relatório do supervisor')
        if pendencias:
            pendencias = ', '.join(pendencias)
            retorno = 'Pendências: {}'.format(pendencias)
        else:
            retorno = 'Sem Pendências.'
        return mark_safe(retorno)

    resumo_pendencias.short_description = 'Resumo de Pendências'

    @property
    def get_atividades(self):
        atividades = ""
        for atividade in self.atividade_set.all():
            atividades += atividade.descricao + ". "
        return atividades

    def notificar(self, user=None):
        if not self.data_fim:
            self.notificar_avaliacao_semestral_aluno(notificar_se_pendente=True)
            self.notificar_avaliacao_semestral_supervisor(notificar_se_pendente=True)
            self.notificar_visitas_pendentes(user)
            self.verificar_matricula_irregular()

    def notificar_visitas_pendentes(self, user=None):
        if not self.data_fim:
            for periodo in self.get_periodos_trimestrais():
                if (
                    datetime.date.today() >= periodo['fim']
                    and not self.visitapraticaprofissional_set.filter(data_visita__range=(periodo['inicio'], periodo['fim'])).exists()
                    and not self.justificativavisitaestagio_set.filter(inicio=periodo['inicio'], fim=periodo['fim']).exists()
                ):
                    url_servidor = Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')
                    titulo = '[SUAP] Pendência de Visita de Orientação de Estágio'
                    assunto = (
                        '<h1>Estágios</h1>'
                        '<h2>Pendência de Visita de Orientação de Estágio</h2>'
                        '<p>Prezado(a) orientador(a), de acordo com as informações enviadas no momento de cadastro do estágio de {}, deve ser realizada e registrada ao menos uma visita durante o período: {} a {}.</p>'
                        '<p>Caso não tenha realizado a visita, por favor, entrar em contato com a concedente para proceder o agendamento.</p>'
                        '<p>Este estágio se iniciou em {} e está prevista para finalizar em {}.</p>'
                        '<p>Informamos que a visita deve ser registrada em formulário próprio disponível no link: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/estagios/modelos-e-formularios/relatorio-de-visita-a-organizacao-concedente/view</p>'
                        '<p>Para registrar a visita, acesse o endereço a seguir: '
                        '<a href="{}accounts/login/?next=/estagios/pratica_profissional/{}/?tab=visitas">Visitas</a>.</p>'
                        '<p>Em caso de dúvidas, procure a Coordenação responsável por estágios no seu Campus.</p>'.format(
                            self.aluno, format_(periodo['inicio']), format_(periodo['fim']), format_(self.data_inicio), format_(self.data_prevista_fim), url_servidor, self.pk
                        )
                    )

                    send_notification(titulo, assunto, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
                    if self.orientador.vinculo.user.email:
                        notificacao = NotificacaoPendencia(
                            pratica_profissional=self,
                            data=datetime.datetime.now(),
                            tipo=NotificacaoPendencia.NOTIFICACAO_VISITA_TRIMESTRAL,
                            notificador=user,
                            email_destinatario=self.orientador.vinculo.user.email,
                            mensagem_enviada='{}<br/>{}'.format(titulo, assunto),
                        )
                        notificacao.save()
                        trimestre_notificado = TrimestreNaoVisitadoNotificado(notificacao=notificacao, inicio=periodo['inicio'], fim=periodo['fim'])
                        trimestre_notificado.save()

    def notificar_avaliacao_semestral_supervisor(self, notificar_se_pendente=False, user=None):
        if self.ha_pendencia_relatorio_supervisor():
            periodos_semestrais = self.get_periodos_semestrais()
            semestre = 1
            for periodo in periodos_semestrais:
                if (
                    periodo['fim'] < datetime.date.today()
                    and not self.relatoriosemestralestagio_set.filter(eh_relatorio_do_supervisor=True, inicio=periodo['inicio'], fim=periodo['fim']).exists()
                    and (
                        not RelatorioSemestralPendenteNotificado.objects.filter(
                            eh_relatorio_do_supervisor=True,
                            inicio=periodo['inicio'],
                            fim=periodo['fim'],
                            notificacao__pratica_profissional=self,
                            notificacao__data__date__gte=datetime.date.today() + datetime.timedelta(-10),
                        ).exists()
                        or notificar_se_pendente
                    )
                ):
                    url_servidor = Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')
                    titulo = '[SUAP] Notificação de Avaliação Semestral de Estagiário sob sua Supervisão'
                    assunto = (
                        '<h1>Aviso de Avaliação Semestral de Estagiário sob sua Supervisão</h1>'
                        '<p>Prezado(a) supervisor(a), solicitamos que cadastre em nosso sistema o Relatório de Atividades de estágio de {}.</p>'
                        '<p>Esta notificação se refere ao {}º período semestral, e este relatório pode ser enviado a partir do dia {}.</p>'
                        '<p>Informamos que o relatório deve ser preenchido em formulário próprio disponível no link: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/estagios/modelos-e-formularios/relatorio-de-atividades-de-estagio-supervisor/view</p>'
                        '<p>Para registrar o relatório, acesse o endereço a seguir: '
                        '<a href="{}estagios/avaliar_pratica_profissional_supervisor/?matricula='
                        '{}&codigo_verificador={}&email_supervisor={}">Avaliar Estágio</a>.</p>'
                        '<p>Agradecemos a sua contribuição na formação do nosso aluno.</p>'.format(
                            self.aluno,
                            semestre,
                            format_(periodo['fim'] + datetime.timedelta(1)),
                            url_servidor,
                            self.aluno.matricula,
                            self.codigo_verificador[0:6],
                            self.email_supervisor,
                        )
                    )
                    send_mail(titulo, assunto, settings.DEFAULT_FROM_EMAIL, [self.email_supervisor])
                    notificacao = NotificacaoPendencia(
                        pratica_profissional=self,
                        data=datetime.datetime.now(),
                        tipo=NotificacaoPendencia.NOTIFICACAO_RELATORIO_SEMESTRAL_SUPERVISOR,
                        notificador=user,
                        email_destinatario=self.email_supervisor,
                        mensagem_enviada='{}<br/>{}'.format(titulo, assunto),
                    )
                    notificacao.save()
                    relatorio_pendente_notificado = RelatorioSemestralPendenteNotificado(
                        eh_relatorio_do_supervisor=True, inicio=periodo['inicio'], fim=periodo['fim'], notificacao=notificacao
                    )
                    relatorio_pendente_notificado.save()

    def notificar_avaliacao_semestral_aluno(self, notificar_se_pendente=False, user=None):
        periodos = self.get_periodos_semestrais()
        for periodo in periodos:
            if (
                periodo['fim'] < datetime.date.today()
                and not self.get_relatorios_estagiario.filter(inicio=periodo['inicio'], fim=periodo['fim']).exists()
                and (
                    not RelatorioSemestralPendenteNotificado.objects.filter(
                        eh_relatorio_do_supervisor=False,
                        inicio=periodo['inicio'],
                        fim=periodo['fim'],
                        notificacao__pratica_profissional=self,
                        notificacao__data__date__gte=datetime.date.today() + datetime.timedelta(-10),
                    ).exists()
                    or notificar_se_pendente
                )
            ):
                url_servidor = Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')
                titulo = '[SUAP] Notificação de Envio de Relatório de Atividades de Estágio'
                assunto = (
                    '<h1>Estágios</h1>'
                    '<h2>Notificação de Relatório Semestral Pendente</h2>'
                    '<p>Prezado(a) estagiário(a), solicitamos que registre no SUAP o seu Relatório de Atividades de Estágio.</p>'
                    'Esta notificação se refere ao período semestral que vai de {} até {}, e este relatório pode ser enviado a partir do dia {}.</p> '
                    '<p>Informamos que o relatório deve ser preenchido em formulário próprio, e assinado pelo(a) orientador(a) e supervisor(a) de estágio. O modelo encontra-se disponível no link: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/estagios/modelos-e-formularios/relatorio-semestral-de-atividades-de-estagio/view <br/>'
                    '<p>Para registrar o relatório, acesse o link a seguir: '
                    '<a href="{}accounts/login/?next=/estagios/pratica_profissional/{}/?tab=relatorios">Relatórios</a></p>'
                    '<p>Em caso de dúvidas, procure a Coordenação responsável por estágios no seu Campus.</p>'.format(
                        format_(periodo['inicio']), format_(periodo['fim']), format_(periodo['fim'] + datetime.timedelta(1)), url_servidor, self.pk
                    )
                )

                send_notification(titulo, assunto, settings.DEFAULT_FROM_EMAIL, [self.aluno.get_vinculo()])
                email_destinatario = self.get_email_aluno()
                if email_destinatario:
                    notificacao = NotificacaoPendencia(
                        pratica_profissional=self,
                        data=datetime.datetime.now(),
                        tipo=NotificacaoPendencia.NOTIFICACAO_RELATORIO_SEMESTRAL_ALUNO,
                        notificador=user,
                        email_destinatario=email_destinatario,
                        mensagem_enviada='{}<br/>{}'.format(titulo, assunto),
                    )
                    notificacao.save()
                    relatorio_pendente_notificado = RelatorioSemestralPendenteNotificado(
                        eh_relatorio_do_supervisor=False, inicio=periodo['inicio'], fim=periodo['fim'], notificacao=notificacao
                    )
                    relatorio_pendente_notificado.save()

    def notificar_apto_para_conclusao(self, user=None):
        titulo = '[SUAP] Estágio Apto para Encerramento'

        assunto = (
            '<h1>Estágio Apto para Encerramento</h1>'
            '<p>Prezados(as) supervisor(a), orientador(a) e estagiário(a),</p>'
            '<p>Notificamos que o estágio do(a) aluno(a) {} na concedente {} encontra-se apto para encerramento.</p>'
            '<p>O termo de Realização de Estágio pode ser encontrado no seguinte link: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/estagios/modelos-e-formularios/termo-de-realizacao-do-estagio/view</p>'
            '<p>Para mais informações e esclarecimentos, entrar em contato com a Coordenação responsável por estágios no respectivo campus.</p>'
            '<p>Agradecemos a sua contribuição na formação do nosso aluno(a).</p>'.format(self.aluno, self.empresa)
        )
        vinculos = [self.orientador.vinculo, self.aluno.get_vinculo()]
        destinatarios = [self.orientador.vinculo.user.email, self.email_supervisor]
        email_aluno = self.get_email_aluno()
        if email_aluno:
            destinatarios.append(email_aluno)

        if not self.notificacaopendencia_set.filter(tipo=NotificacaoPendencia.NOTIFICACAO_APTO_PARA_CONCLUSAO).exists():
            send_notification(titulo, assunto, settings.DEFAULT_FROM_EMAIL, vinculos)
            notificao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_APTO_PARA_CONCLUSAO,
                notificador=user,
                email_destinatario=', '.join(destinatarios),
                mensagem_enviada='{}<br/>{}'.format(titulo, assunto),
            )
            notificao.save()

    def get_email_aluno(self):

        if self.aluno.pessoa_fisica.email_secundario:
            return self.aluno.pessoa_fisica.email_secundario
        elif self.aluno.pessoa_fisica.email:
            return self.aluno.pessoa_fisica.email
        elif self.aluno.email_academico:
            return self.aluno.email_academico
        else:
            return None

    def atualiza_status(self):
        """
            atualizando o status do estágio:

            - se estágio não foi encerrado
                - se tempo do estágio < 3 meses OU (tempo do estágio >= 3 meses E (quant. pendente de visitas - quant. de visitas) > 0)
                    aguardando visita do orientador
                - se tempo do estágio < 6 meses OU (tempo do estágio >= 6 meses E (quant. pendente de rel. superv. - quant. de rel. superv.) > 0)
                    aguardando relatório do supervisor
                - se tempo do estágio < 6 meses OU (tempo do estágio >= 6 meses E (quant. pendente de rel. estag. - quant. de rel. estag.) > 0)
                    aguardando relatório do estagiário
                - se (não está aguardando visita do orientador) E
                     (não está aguardando relatório do supervisor) E
                     (não está aguardando relatório do estagiário)
                    - se (quant. esperada de visitas = quant. de visitas) E
                         (quant. esperada de rel. superv. = quant. de rel. superv.) E
                         (quant. esperada de rel. estag. = quant. de rel. estag.)
                        - se foi avaliado pelo estagiário
                            apto para conclusão
                        - senão
                            aguardando avaliação do estagiário
                    - senão
                        em andamento
                - senão
                    - se aguardando visita do orientador E aguardando relatório do supervisor E aguardando relatório do estagiário
                        aguardando visita do orientador, relatório do supervisor e relatório do estagiário
                    - senão se aguardando visita do orientador E aguardando relatório do supervisor
                        aguardando visita do orientador e relatório do supervisor
                    - senão se aguardando visita do orientador E aguardando relatório do estagiário
                        aguardando visita do orientador e relatório do estagiário
                    - senão se aguardando relatório do supervisor E aguardando relatório do estagiário
                        aguardando relatório do supervisor e relatório do estagiário
                    - senão se aguardando visita do orientador
                        aguardando visita do orientador
                    - senão se aguardando relatório do supervisor
                        aguardando relatório do supervisor
                    - senão se aguardando relatório do estagiário
                        aguardando relatório do estagiário
            - se estágio foi encerrado por motivo de rescisão
                rescindido
            - se estágio foi encerrado E é anterior a 20161
                concluído
        """
        #
        if not self.data_fim:
            self.status = PraticaProfissional.STATUS_EM_ANDAMENTO
            if self.data_prevista_fim < datetime.date.today() and (self.pendente_relatorio_estagiario or self.pendente_relatorio_supervisor or self.pendente_visita):
                self.status = self.STATUS_COM_PENDENCIA

            if not self.pendente_relatorio_estagiario and not self.pendente_relatorio_supervisor and not self.pendente_visita and self.data_prevista_fim < datetime.date.today():
                self.status = self.STATUS_APTO_PARA_CONCLUSAO
                self.notificar_apto_para_conclusao()
        #
        elif self.movito_encerramento == self.MOTIVO_RESCISAO:
            self.status = PraticaProfissional.STATUS_RESCINDIDO  # tem o mesmo o valor de concluído
        elif self.movito_encerramento == self.MOTIVO_CONCLUSAO and not self.pendente_relatorio_estagiario and not self.pendente_relatorio_supervisor and not self.pendente_visita:
            self.status = PraticaProfissional.STATUS_CONCLUIDO
        elif self.estagio_anterior_20161:
            self.status = PraticaProfissional.STATUS_CONCLUIDO
        else:
            self.status = PraticaProfissional.STATUS_CONCLUIDO

    @property
    def foi_rescidido(self):
        return self.movito_encerramento == self.MOTIVO_RESCISAO

    @property
    def is_tempo_estagio_menor_que_3_meses(self):
        return self.get_qtd_dias() < 90

    @property
    def is_tempo_estagio_3_meses_ou_mais(self):
        return not self.is_tempo_estagio_menor_que_3_meses

    @property
    def is_tempo_estagio_menor_que_6_meses(self):
        return self.get_qtd_dias() < 180  # 6 meses = 180 dias

    @property
    def is_tempo_estagio_6_meses_ou_mais(self):
        return not self.is_tempo_estagio_menor_que_6_meses

    @property
    def get_qtd_pendente_visitas_orientador(self):
        qtd = self.get_qtd_esperada_visitas_orientador - self.get_qtd_visitas_orientador
        if qtd < 0:
            qtd = 0
        return qtd

    @property
    def get_qtd_esperada_visitas_orientador(self):
        return self.get_qtd_trimestres()

    @property
    def get_qtd_visitas_orientador(self):
        return self.visitapraticaprofissional_set.all().count()

    @property
    def get_qtd_pendente_relatorios_supervisor(self):
        qtd = self.get_qtd_esperada_relatorios_supervisor - self.get_qtd_relatorios_supervisor
        if qtd < 0:
            qtd = 0
        return qtd

    @property
    def get_qtd_esperada_relatorios_supervisor(self):
        # 6 meses = 180 dias
        # ex: 2 meses = 1 relatório; 6 meses e 1 dia = 2 relatórios; 12 meses = 2 relatórios; 12 meses e dia = 3 relat.
        qtd_dias = self.get_qtd_dias()
        quociente = qtd_dias // 180
        resto = qtd_dias % 180
        if resto:
            return quociente + 1
        return quociente

    @property
    def get_qtd_relatorios_supervisor(self):
        return self.relatoriosemestralestagio_set.filter(eh_relatorio_do_supervisor=True).count()

    @property
    def get_relatorios_supervisor(self):
        return self.relatoriosemestralestagio_set.filter(eh_relatorio_do_supervisor=True).order_by('inicio')

    @property
    def get_nota_media_relatorios_supervisor(self):
        return self.relatoriosemestralestagio_set.filter(eh_relatorio_do_supervisor=True).aggregate(Avg('nota_estagiario'))['nota_estagiario__avg']

    @property
    def get_qtd_pendente_relatorios_estagiario(self):
        qtd_relatorios_pendentes = 0
        for periodo in self.get_periodos_semestrais():
            if periodo['fim'] < datetime.date.today() and not periodo['relatorio_estagiario'].exists():
                qtd_relatorios_pendentes += 1
        return qtd_relatorios_pendentes

    @property
    def get_qtd_esperada_relatorios_estagiario(self):
        return self.get_qtd_esperada_relatorios_supervisor  # idem supervisor

    @property
    def get_qtd_relatorios_estagiario(self):
        return self.relatoriosemestralestagio_set.filter(eh_relatorio_do_supervisor=False).count()

    @property
    def get_relatorios_estagiario(self):
        return self.relatoriosemestralestagio_set.filter(eh_relatorio_do_supervisor=False).order_by('inicio')

    def __str__(self):
        return 'Estágio de {} em {}'.format(self.aluno, self.empresa)

    def get_absolute_url(self):
        return '/estagios/pratica_profissional/{}/'.format(self.pk)

    def clean(self):
        # O Estagiário só pode ter um estágio ativo
        if self.aluno_id is None:
            raise ValidationError('O campo estagiário é obrigatório.')
        if self.orientador_id is None:
            raise ValidationError('O campo orientador é obrigatório.')
        if self.empresa_id is None:
            raise ValidationError('O campo concedente é obrigatório.')
        if self.aluno_id is None and self.aluno.praticaprofissional_set.filter(data_fim__isnull=False).exclude(pk=self.pk).count():
            raise ValidationError('O estagiário possui uma prática profissional em andamento.')

        # Caso a prática profissional seja do tipo prática profissional efetiva, é obrigatório preencher Documentação
        # Comprobatória.
        if self.tipo == self.TIPO_ATIVIDADE_PROFISSIONAL and not self.documentacao_comprobatoria:
            raise ValidationError(
                {'documentacao_comprobatoria': 'Caso a prática profissional seja do tipo Prática ' 'Profissional Efetiva, a Documentação Comprobatória ' 'é obrigatória.'}
            )

        if not self.pk and self.aluno.situacao in get_situacoes_irregulares():
            raise ValidationError({'aluno': 'Aluno com situação {} não pode estagiar.'.format(self.aluno.situacao.descricao)})

        if self.aluno.curso_campus.modalidade not in Modalidade.objects.filter(
            id__in=[
                Modalidade.LICENCIATURA,
                Modalidade.ENGENHARIA,
                Modalidade.BACHARELADO,
                Modalidade.INTEGRADO,
                Modalidade.INTEGRADO_EJA,
                Modalidade.SUBSEQUENTE,
                Modalidade.CONCOMITANTE,
                Modalidade.TECNOLOGIA,
            ]
        ):
            raise ValidationError(
                {
                    'aluno': 'Este aluno é da modalidade {}. Somente alunos das modalidades Licenciatura, Engenharia, Integrado, Integrado Eja, Subsequente e Tecnologia podem estagiar.'.format(
                        self.aluno.curso_campus.modalidade.descricao
                    )
                }
            )

        if not self.aluno.matriz:
            raise ValidationError({'aluno': 'Aluno sem matriz não pode ser cadastrado.'})
        else:
            percentual_disciplinas_obrigatorias = (
                self.aluno.get_ch_componentes_regulares_obrigatorios_cumprida() * 100 / self.aluno.get_ch_componentes_regulares_obrigatorios_esperada()
            )
            if self.obrigatorio:
                if self.aluno.matriz.periodo_minimo_estagio_obrigatorio and self.aluno.periodo_atual < self.aluno.matriz.periodo_minimo_estagio_obrigatorio:
                    raise ValidationError(
                        {
                            'aluno': 'Esse aluno encontra-se no {}º período de referência. Nesse curso, '
                            'só é permitido iniciar um ESTÁGIO OBRIGATÓRIO a partir do {}º período.'.format(
                                self.aluno.periodo_atual, self.aluno.matriz.periodo_minimo_estagio_obrigatorio
                            )
                        }
                    )
            else:
                periodo_obrigatorio = self.aluno.matriz.periodo_minimo_estagio_nao_obrigatorio or 0
                periodo_atual = self.aluno.periodo_atual or 1
                if not percentual_disciplinas_obrigatorias >= 50 and not periodo_obrigatorio <= periodo_atual:
                    raise ValidationError(
                        {
                            'aluno': 'Esse aluno encontra-se no {}º período de referência e '
                            'tem {}% da carga horária integralizada. Nesse curso, '
                            'só é permitido iniciar um ESTÁGIO NÃO OBRIGATÓRIO a '
                            'partir do {}º período de referência ou após ter ao menos '
                            '50% das disciplinas obrigatórias integralizadas.'.format(periodo_atual, percentual_disciplinas_obrigatorias, periodo_obrigatorio)
                        }
                    )

    def atingiu_data_prevista_fim(self):
        return self.data_prevista_fim <= datetime.date.today()

    def get_datas_limite_para_envio_relatorios_semestrais(self):
        datas_limite = []
        for periodo in self.get_periodos_semestrais():
            datas_limite.append(periodo['fim'])
        return datas_limite

    def get_datas_limite_para_visitas_trimestrais(self):
        datas_limite = []
        for periodo in self.get_periodos_trimestrais():
            datas_limite.append(periodo['fim'])
        return datas_limite

    def get_datas_limite_para_visitas_trimestrais_estagio_menor_180_dias(self):
        delta = self.data_prevista_fim - self.data_inicio
        datas_limite = []
        data_limite = self.data_inicio + datetime.timedelta(delta.days / 2)
        datas_limite.append(data_limite)
        return datas_limite

    def get_qtd_dias(self):
        return (self.data_prevista_fim - self.data_inicio).days + 1

    def get_qtd_meses_e_dias(self):
        return relativedelta(self.data_prevista_fim, self.data_inicio)

    def get_qtd_trimestres(self):
        trimestres = abs(self.get_qtd_dias() / 90)
        if trimestres <= 0:
            trimestres = 1
        return int(trimestres)

    def get_periodos_semestrais(self):
        periodos_semestrais = self.get_periodos()
        for periodo in periodos_semestrais:
            periodo['relatorio_estagiario'] = self.relatoriosemestralestagio_set.filter(eh_relatorio_do_supervisor=False, inicio=periodo['inicio'], fim=periodo['fim'])
            periodo['relatorio_supervisor'] = self.relatoriosemestralestagio_set.filter(eh_relatorio_do_supervisor=True, inicio=periodo['inicio'], fim=periodo['fim'])
        return periodos_semestrais

    def get_periodos_trimestrais(self):
        periodos = self.get_periodos(meses=3)
        if len(periodos) > 1:
            ultimo_periodo = periodos[-1:][0]
            deveria_ser_fim = (ultimo_periodo['inicio'] + relativedelta(months=+3)) - datetime.timedelta(1)
            if ultimo_periodo['fim'] < deveria_ser_fim:
                periodos = periodos[0:-1]
        for periodo in periodos:
            periodo['visitas'] = self.visitapraticaprofissional_set.filter(data_visita__range=(periodo['inicio'], periodo['fim']))
            periodo['justificativa'] = self.justificativavisitaestagio_set.filter(inicio=periodo['inicio'], fim=periodo['fim'])
        return periodos

    def get_periodos(self, meses=6):
        data_fim = self.data_prevista_fim
        periodos = []
        inicio_prox_periodo = self.data_inicio
        while True:
            fim_prox_periodo = (inicio_prox_periodo + relativedelta(months=+meses)) - datetime.timedelta(1)
            if fim_prox_periodo > data_fim:
                fim_prox_periodo = data_fim
            if inicio_prox_periodo != fim_prox_periodo:
                periodos.append({'inicio': inicio_prox_periodo, 'fim': fim_prox_periodo})
            if fim_prox_periodo != data_fim:
                inicio_prox_periodo = fim_prox_periodo + datetime.timedelta(1)
            else:
                break
        if len(periodos) == 0:
            periodos.append({'inicio': inicio_prox_periodo, 'fim': fim_prox_periodo})
        return periodos

    def get_qtd_relatorios_semestrais_pendentes(self):
        return max(0, len(self.get_periodos_semestrais()) - self.relatoriosemestralestagio_set.count())

    def get_campus(self):
        return '{}'.format(self.aluno.curso_campus.diretoria.setor.uo)

    get_campus.admin_order_field = 'aluno__curso_campus__diretoria__setor__uo'
    get_campus.short_description = 'Campus'

    def get_situacao_aluno(self):
        return '{}'.format(self.aluno.situacao)

    get_situacao_aluno.admin_order_field = 'aluno__situacao__descricao'
    get_situacao_aluno.short_description = 'Situação do Estagiário'

    def get_situacao_ultima_matricula_periodo(self):
        return '{}'.format(self.aluno.get_ultima_matricula_periodo().situacao)

    get_situacao_ultima_matricula_periodo.admin_order_field = 'aluno__matriculaperiodo__situacao__descricao'
    get_situacao_ultima_matricula_periodo.short_description = 'Situação da Matrícula no Período'

    def get_aditivo(self):
        lista = ['<ul>']
        for aditivo in self.estagioaditivocontratual_set.all():
            lista.append('<li>{}</li>'.format(aditivo))
        lista.append('</ul>')
        return mark_safe(''.join(lista))

    get_aditivo.short_description = 'Aditivos Contratuais'

    def get_sugestao_ch_final(self):
        dias = numpy.busday_count(self.data_inicio, self.data_prevista_fim + datetime.timedelta(days=1))
        ch_sugerida = dias * (self.ch_semanal / Decimal(5.0))
        return (
            'Dada a data cadastrada de início e a data prevista para fim deste estágio, considerando-se apenas '
            'os dias de trabalho (segunda a sexta), estima-se uma carga horária de {} horas de trabalho. Deste '
            'total não são excluídos feriados e nem outras possíveis interrupções do trabalho na concedente.'.format(format_(ch_sugerida))
        )

    def eh_concluido(self):
        return self.status == self.STATUS_CONCLUIDO or self.status == self.STATUS_RESCINDIDO

    def enviar_emails_estagio_recem_cadastrado(self, user=None):
        self.save()
        self.enviar_email_supervisor_recem_cadastrado()

        titulo_orientador = '[SUAP] Cadastro como Orientador de Estágio'
        texto_orientador = (
            '<h1>Cadastro como Orientador de Estágio</h1>'
            '<p>Caro, {}, você foi cadastrado como orientador de estágio de {}.</p>'
            '<p>Você é o responsável na instituição de ensino pelo acompanhamento do desenvolvimento das atividades de estágio, '
            'pela realização das visitas trimestrais (datas listadas abaixo) e seu cadastro em nosso sistema, além de acompanhar '
            'a elaboração e envio dos relatórios de atividades de estágio.</p>'.format(self.orientador.vinculo.pessoa.nome, self.aluno)
        )
        texto_orientador += '<dl>'
        for periodo in self.get_periodos_trimestrais():
            texto_orientador += '<dt>Período:</dt><dd>De {} até {}</dd>'.format(format_(periodo['inicio']), format_(periodo['fim']))
        texto_orientador += '<dt>Manual do Orientador:</dt><dd>http://portal.ifrn.edu.br/extensao/estagios-e-egressos/estagios/manuais-de-utilizacao-do-suap</dd>'
        texto_orientador += '</dl>'
        texto_orientador += '<p>Mais informações sobre o estágio estão disponíveis no seu SUAP > Serviços > Professor > Orientações de Estágio.</p>'
        texto_orientador += '<p>Em caso de dúvidas, procure a Coordenação responsável por estágios no seu Campus.</p>'

        send_notification(titulo_orientador, texto_orientador, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
        if self.orientador.vinculo.user.email:
            notificao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_INICIAL,
                notificador=user,
                email_destinatario=self.orientador.vinculo.user.email,
                mensagem_enviada='{}<br/>{}'.format(titulo_orientador, texto_orientador),
            )
            notificao.save()

        titulo_estagiario = '[SUAP] Cadastro de Estágio'
        texto_estagiario = (
            '<p>Caro, {}, você foi cadastrado como estagiário, sob orientação do professor {}. '
            'Você é responsável também pelo acompanhamento do andamento do seu estágio. '
            'A cada período de 6 meses, ou menos, de acordo com o prazo do seu estágio, '
            'você deve elaborar, com vistas ao seu professor orientador e supervisor de estágio, um Relatório de Atividade de Estágio.</p>'.format(
                self.aluno, self.orientador.vinculo.pessoa.nome
            )
        )
        texto_estagiario += '<dl>'
        for periodo in self.get_periodos_semestrais():
            texto_estagiario += '<dt>Período:</dt><dd>De {} até {}. O envio do relatório pode ser feito após o dia {}.</dd>'.format(
                format_(periodo['inicio']), format_(periodo['fim']), format_(periodo['fim'])
            )
        texto_estagiario += '<dt>Manual do Estagiário:</dt><dd>http://portal.ifrn.edu.br/extensao/estagios-e-egressos/estagios/manuais-de-utilizacao-do-suap</dd>'
        texto_estagiario += '</dl>'
        texto_estagiario += '<p>Mais informações sobre o seu estágio estão disponíveis no seu SUAP > Menu Lateral > Ensino > Dados do Aluno > Aba: Prática Profissional.</p>'
        texto_estagiario += '<p>Em caso de dúvidas, procure a Coordenação responsável por estágios no seu Campus.</p>'
        send_notification(titulo_estagiario, texto_estagiario, settings.DEFAULT_FROM_EMAIL, [self.aluno.get_vinculo()])
        email_destinatario = self.get_email_aluno()
        if email_destinatario:
            notificao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_INICIAL,
                notificador=user,
                email_destinatario=email_destinatario,
                mensagem_enviada='{}<br/>{}'.format(titulo_estagiario, texto_estagiario),
            )
            notificao.save()

    def enviar_email_supervisor_recem_cadastrado(self, user=None):
        titulo_supervisor = '[SUAP] Cadastro como Supervisor de Estágio'
        texto_supervisor = (
            '<h1>Cadastro como Supervisor de Estágio</h1>'
            '<p>Caro, {}, você foi cadastrado como supervisor de estágio de {}.</p>'
            '<p>Você é responsável por acompanhar o desenvolvimento das atividades de estágio e realizar em nosso sistema (datas abaixo), '
            'o cadastro dos Relatórios de Atividades de Estágio. Em cada período de referência para o envio desses relatórios, você receberá um '
            'e-mail com as informações de acesso ao sistema.</p>'.format(self.nome_supervisor, self.aluno)
        )
        texto_supervisor += '<dl>'
        for periodo in self.get_periodos_semestrais():
            texto_supervisor += '<dt>Período:</dt><dd>de {} até {}. O envio do relatório pode ser feito após o dia {}.</dd>'.format(
                format_(periodo['inicio']), format_(periodo['fim']), format_(periodo['fim'])
            )
        texto_supervisor += '<dt>Manual do Supervisor:</dt><dd>http://portal.ifrn.edu.br/extensao/estagios-e-egressos/estagios/manuais-de-utilizacao-do-suap</dd>'
        texto_supervisor += '</dl>'
        texto_supervisor += (
            '<p>Caso necessite entrar em contato conosco basta buscar o telefone do campus na página: portal.ifrn.edu.br ou no termo de compromisso'
            'de estágio, ou, ainda, entrar em contato com o professor orientador, através do seguinte e-mail: {}.</p>'.format(self.orientador.vinculo.pessoa.email)
        )
        texto_supervisor += '<p>Desde já agradecemos sua contribuição com nosso aluno.</p>'
        send_mail(titulo_supervisor, texto_supervisor, settings.DEFAULT_FROM_EMAIL, [self.email_supervisor])
        notificao = NotificacaoPendencia(
            pratica_profissional=self,
            data=datetime.datetime.now(),
            tipo=NotificacaoPendencia.NOTIFICACAO_INICIAL,
            notificador=user,
            email_destinatario=self.email_supervisor,
            mensagem_enviada='{}<br/>{}'.format(titulo_supervisor, texto_supervisor),
        )
        notificao.save()

    def get_periodo_duracao(self):
        if self.data_fim:
            return [self.data_inicio, self.data_fim]
        else:
            return [self.data_inicio, self.data_prevista_fim]

    def verificar_pendencias(self):
        self.verificar_visitas_pendentes()
        self.notificar_avaliacao_semestral_supervisor()
        self.notificar_avaliacao_semestral_aluno()

    def verificar_matricula_irregular(self):
        # se ocorreu matrícula irregular por parte de um aluno
        if self.aluno.situacao in get_situacoes_irregulares() and not self.prazo_final_regularizacao_matricula_irregular:
            self.prazo_final_regularizacao_matricula_irregular = datetime.date.today() + relativedelta(days=7)
            self.save()
            self.notificar_aluno_matricula_irregular()
            self.notificar_supervisor_aluno_matricula_irregular()
            self.notificar_coordenador_aluno_matricula_irregular()
            self.notificar_orientador_aluno_matricula_irregular()

            self.notificar_coordenacao_extensao_aluno_matricula_irregular()
        # se foi dado prazo e o aluno regularizou a matrícula
        if (
            self.aluno.situacao not in get_situacoes_irregulares()
            and self.prazo_final_regularizacao_matricula_irregular
            and not self.notificacaopendencia_set.filter(tipo=NotificacaoPendencia.NOTIFICACAO_FINAL_MATRICULA_IRREGULAR).exists()
        ):
            self.prazo_final_regularizacao_matricula_irregular = None
            self.notificar_supervisor_aluno_matricula_regularizada()
            self.notificar_orientador_aluno_matricula_regularizada()
            self.save()
        # se a situacao irregular persistiu por mais de 7 dias
        if (
            self.aluno.situacao in get_situacoes_irregulares()
            and self.prazo_final_regularizacao_matricula_irregular
            and self.prazo_final_regularizacao_matricula_irregular < datetime.date.today()
            and not self.notificacaopendencia_set.filter(tipo=NotificacaoPendencia.NOTIFICACAO_FINAL_MATRICULA_IRREGULAR).exists()
        ):
            self.notificar_aluno_interrupcao()
            self.notificar_supervisor_interrupcao()
            self.notificar_orientador_interrupcao()

    def notificar_aluno_matricula_irregular(self):
        instituicao_sigla = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
        titulo = '[SUAP] Matrícula Irregular'
        mensagem = (
            '<h1>Estágios</h1>'
            '<h2>[SUAP] Matrícula Irregular</h2>'
            '<p>Caro (a), {}, sua matrícula no curso {}, encontra-se com a seguinte situação irregular: <strong>{}</strong>. '
            'Verificamos que você possui um Cadastro de Estágio com duração até {}. A matrícula e a '
            'frequência regulares são pré-requisitos para a manutenção desse vínculo.</p>'
            '<p>É necessário que você procure o {} (Secretaria Acadêmica e Setor de Estágios/Extensão) para '
            'regularizar sua situação até o dia <strong>{}</strong>. Em caso de não comparecimento, informaremos a empresa '
            'para que providências legais cabíveis sejam tomadas.</p>'.format(
                self.aluno,
                self.aluno.curso_campus,
                self.aluno.situacao,
                format_(self.data_prevista_fim),
                instituicao_sigla,
                format_(self.prazo_final_regularizacao_matricula_irregular),
            )
        )

        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.aluno.get_vinculo()])
        email_aluno = self.get_email_aluno()
        if email_aluno:
            notificao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=email_aluno,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_supervisor_aluno_matricula_irregular(self):
        titulo = '[SUAP] Notificação de Estagiário com Matrícula Irregular'
        mensagem = (
            '<h1>Estágios</h1>'
            '<h2>[SUAP] Notificação de Estagiário com Matrícula Irregular</h2>'
            '<p>Caro (a), {}, informamos que o (a) Estagiário (a) {} que se encontra sob sua supervisão, '
            'está com a matrícula em situação irregular: <strong>{}</strong>. O (a) aluno (a) tem até o dia <strong>{}</strong> para '
            'regularizar sua matrícula junto a nossa instituição. Após o prazo estabelecido, '
            'informaremos sobre a situação do (a) estudante.</p>'
            '<p>Lembramos que se um estagiário estiver com frequência no local de trabalho, e não '
            'comprovar a regularidade de sua matrícula junto a empresa, poderá ser caracterizado '
            '<b>vínculo empregatício</b>, conforme o § 2o do Artigo 3º da Lei 11.788/08.</p>'
            '<p>Caso o (a) estudante ou a empresa tenha realizado a rescisão, pedimos o envio do Termo de '
            'Realização de Estágio, disponível no link: '
            'http://portal.ifrn.edu.br/extensao/estagios-e-egressos/estagios/modelos-e-formularios/. </p>'.format(
                self.nome_supervisor, self.aluno, self.aluno.situacao, format_(self.prazo_final_regularizacao_matricula_irregular)
            )
        )
        if self.email_supervisor:
            send_mail(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.email_supervisor])
            notificao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=self.email_supervisor,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_coordenador_aluno_matricula_irregular(self):
        titulo = '[SUAP] Notificação de Estagiário com Matrícula Irregular'
        mensagem = (
            '<h1>Estágios</h1>'
            '<h2>[SUAP] Notificação de Estagiário com Matrícula Irregular</h2>'
            '<p>Caro(a), {}, informamos que o (a) estudante {}, tem um cadastro de estágio em aberto '
            'e está com a matrícula em situação irregular: <strong>{}</strong>. O (a) aluno (a) tem até o dia <strong>{}</strong> para '
            'regularizar sua matrícula junto a nossa instituição. </p>'
            '<p>Informamos que se um estagiário estiver com frequência no local de trabalho, e não '
            'comprovar a regularidade de sua matrícula junto a empresa, poderá ser caracterizado <b>vínculo '
            'empregatício</b>, conforme o § 2o do Artigo 3º da Lei 11.788/08. Caso o (a) aluno (a) não '
            'regularize sua situação, a empresa será notificada para que tome as providências legais cabíveis.</p>'
            '<p>É importante averiguar a situação em que se encontra o(a) estudante e entrar em contato com a '
            'Coordenação de Estágios/Extensão do Campus.</p>'.format(
                self.aluno.curso_campus.coordenador.nome, self.aluno, self.aluno.situacao, format_(self.prazo_final_regularizacao_matricula_irregular)
            )
        )

        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.aluno.curso_campus.coordenador.get_vinculo()])
        if self.aluno.curso_campus.coordenador.user.email:
            notificao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=self.aluno.curso_campus.coordenador.user.email,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_orientador_aluno_matricula_irregular(self):
        titulo = '[SUAP] Notificação de Estagiário com Matrícula Irregular'
        mensagem = (
            '<h1>Estágios</h1>'
            '<h2>[SUAP] Notificação de Estagiário com Matrícula Irregular</h2>'
            '<p>Caro(a), {}, informamos que o (a) estudante {}, tem um cadastro de estágio em aberto e '
            'está com a matrícula em situação irregular: <strong>{}</strong>. O (a) aluno (a) tem até o dia <strong>{}</strong> para '
            'regularizar sua matrícula junto a nossa instituição. </p>'
            '<p>Informamos que se um estagiário estiver com frequência no local de trabalho, e não '
            'comprovar a regularidade de sua matrícula junto a empresa, poderá ser caracterizado <b>vínculo '
            'empregatício</b>, conforme o § 2o do Artigo 3º da Lei 11.788/08. Caso o (a) aluno (a) não '
            'regularize sua situação, a empresa será notificada para que tome as providências legais cabíveis.</p>'
            '<p>É importante averiguar a situação em que se encontra o(a) estudante e entrar em contato com a '
            'Coordenação de Estágios/Extensão do Campus.</p>'.format(
                self.orientador.vinculo.pessoa.nome, self.aluno, self.aluno.situacao, format_(self.prazo_final_regularizacao_matricula_irregular)
            )
        )
        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
        if self.orientador.vinculo.user.email:
            notificao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=self.orientador.vinculo.user.email,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_coordenacao_extensao_aluno_matricula_irregular(self):
        coordenadores = get_coordenadores_estagio(self.aluno)
        coordenadores_nomes = get_coordenadores_nomes(coordenadores)
        coordenadores_emails = get_coordenadores_emails(coordenadores)
        coordenadores_vinculos = get_coordenadores_vinculos(coordenadores)
        titulo = '[SUAP] Notificação de Estagiário com Matrícula Irregular'
        instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
        mensagem = (
            '<h1>Estágios</h1>'
            '<h2>[SUAP] Notificação de Estagiário com Matrícula Irregular</h2>'
            '<p>Caros(as), Coordenadores(as) de Estágio {}, informamos que o(a) estudante {}, tem um cadastro de '
            'estágio em aberto e está com a seguinte situação de matrícula irregular: <strong>{}</strong>. '
            'O(a) aluno(a) tem até o dia {} para regularizar sua matrícula junto ao {}.</p>'
            '<p>Lembramos que se o aluno estiver com frequência no local de trabalho, e não comprovar '
            'a regularidade de sua matrícula junto a empresa, será caracterizado <strong>vínculo empregatício</strong>, '
            'conforme decreto 9.579/2018. <strong>Após o prazo estabelecido a situação '
            'de matrícula do(a) aluno(a) deve ser informada a empresa.</strong></p>'
            'É importante averiguar a situação em que se encontra o(a) estudante para evitar '
            'possíveis prejuízos no relacionamento da empresa com o {} e nosso(a) aluno(a).'.format(
                coordenadores_nomes, self.aluno, self.aluno.situacao.descricao, format_(self.prazo_final_regularizacao_matricula_irregular), instituicao, instituicao
            )
        )

        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, coordenadores_vinculos)
        if coordenadores_emails:
            notificao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=coordenadores_emails,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_supervisor_aluno_matricula_regularizada(self):
        titulo = '[SUAP] Notificação de Regularização de Matrícula de Estagiário'
        mensagem = (
            '<h1>Estágios</h1>'
            '<h2>[SUAP] Notificação de Regularização de Matrícula de Estagiário</h2>'
            '<p>Caro (a), {}, informamos que o (a) estagiário (a) {} que se encontra sob sua supervisão, '
            'está com a matrícula em situação regular: <strong>{}</strong>. Desta forma, o contrato de estágio pode seguir '
            'o prazo previamente estabelecido, até o dia: {}. </p>'
            '<p>Agradecemos a parceria no trabalho desempenhado.</p>'.format(self.nome_supervisor, self.aluno, self.aluno.situacao, format_(self.data_prevista_fim))
        )
        if self.email_supervisor:
            send_mail(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.email_supervisor])
            notificao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_MATRICULA_REGULARIZADA,
                notificador=None,
                email_destinatario=self.email_supervisor,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_orientador_aluno_matricula_regularizada(self):
        titulo = '[SUAP] Notificação de Regularização de Matrícula de Estagiário'
        mensagem = (
            '<h1>Estágios</h1>'
            '<h2>[SUAP] Notificação de Regularização de Matrícula de Estagiário</h2>'
            '<p>Caro (a), {}, informamos que o (a) estagiário (a) {} que se encontra sob sua orientação, '
            'está com a matrícula em situação regular: <strong>{}</strong>. Desta forma, o contrato de estágio pode seguir '
            'o prazo previamente estabelecido, até o dia: {}.</p>'.format(self.orientador.vinculo.pessoa.nome, self.aluno, self.aluno.situacao, format_(self.data_prevista_fim))
        )
        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
        if self.orientador.vinculo.user.email:
            notificao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_MATRICULA_REGULARIZADA,
                notificador=None,
                email_destinatario=self.orientador.vinculo.user.email,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def get_data_envio_notificacao(self):
        notificacoes = self.notificacaopendencia_set.filter(tipo=NotificacaoPendencia.NOTIFICACAO_MATRICULA_IRREGULAR).order_by('data')
        if notificacoes.exists():
            return notificacoes[0].data.date()
        else:
            return None

    def notificar_aluno_interrupcao(self):
        data_envio_notificacao = self.get_data_envio_notificacao()
        titulo = '[SUAP] Notificação de Rescisão/Encerramento de Estágio'
        mensagem = (
            '<h1>Estágios</h1>'
            '<h2>[SUAP] Notificação de Rescisão/Encerramento de Estágio</h2>'
            '<p>Caro (a), {}, de acordo com aviso enviado no dia {}, e diante da ausência de manifestação '
            'de sua parte quanto a sua matrícula irregular, informamos que a empresa foi informada a '
            'respeito da situação e deve tomar as providências legais cabíveis.</p>'.format(self.aluno, format_(data_envio_notificacao))
        )
        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.aluno.get_vinculo()])
        email_aluno = self.get_email_aluno()
        if email_aluno:
            notificao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_FINAL_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=email_aluno,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_supervisor_interrupcao(self):
        coordenadores = get_coordenadores_estagio(self.aluno)
        coordenadores_emails = get_coordenadores_emails(coordenadores)
        titulo = '[SUAP] Notificação de Estagiário com Matrícula Irregular'
        mensagem = (
            '<h1>Estágios</h1>'
            '<h2>[SUAP] Notificação de Estagiário com Matrícula Irregular</h2>'
            '<p>Caro (a), {}, informamos que o (a) estagiário (a) {} que se encontra sob sua supervisão, '
            'não se manifestou a respeito da condição irregular de sua matrícula: {}. Dessa forma, é '
            'necessário que seja feito o encerramento/rescisão.</p>'
            '<p>Lembramos que se um estagiário estiver com frequência no local de trabalho, e não comprovar '
            'a regularidade de sua matrícula junto a empresa, poderá ser caracterizado vínculo empregatício, '
            'conforme o § 2o do Artigo 3º da Lei 11.788/08.</p>'
            '<p>Assim, pedimos que o Termo de Realização de Estágio seja encaminhado para o(s) e-mail(s): {}.</p>'
            '<p>Modelo do Termo de Realização de Estágio: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/estagios/modelos-e-formularios/ </p>'.format(
                self.nome_supervisor, self.aluno, self.aluno.situacao, coordenadores_emails
            )
        )
        if self.email_supervisor:
            send_mail(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.email_supervisor])
            notificao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_FINAL_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=self.email_supervisor,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def notificar_orientador_interrupcao(self):
        titulo = '[SUAP] Notificação de Estagiário com Matrícula Irregular'
        mensagem = (
            '<h1>Estágios</h1>'
            '<h2>[SUAP] Notificação de Estagiário com Matrícula Irregular</h2>'
            '<p>Caro (a), {}, informamos que o (a) estagiário (a) {}, o qual se encontra sob sua orientação, '
            'não se manifestou a respeito da condição irregular de sua matrícula: {}. Desta forma, a empresa '
            'foi informada da situação e deve proceder a rescisão do estágio.</p>'
            '<p>Além disso, é necessário averiguar a situação da prática profissional do(a) estudante, '
            'contabilizando as horas cumpridas, e se cabível, verificando a existência ou não de um '
            'relatório de prática profissional.</p>'.format(self.orientador.vinculo.pessoa.nome, self.aluno, self.aluno.situacao)
        )
        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
        if self.orientador.vinculo.user.email:
            notificao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_FINAL_MATRICULA_IRREGULAR,
                notificador=None,
                email_destinatario=self.orientador.vinculo.user.email,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificao.save()

    def verificar_visitas_pendentes(self, user=None):
        for periodo in self.get_periodos_trimestrais():
            if (
                datetime.date.today() >= periodo['inicio']
                and not self.visitapraticaprofissional_set.filter(data_visita__range=(periodo['inicio'], periodo['fim'])).exists()
                and not self.justificativavisitaestagio_set.filter(inicio=periodo['inicio'], fim=periodo['fim']).exists()
            ):
                if self.deve_enviar_primeira_notificacao_de_visita_trimestral(periodo):
                    url_servidor = Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')
                    titulo = '[SUAP] Lembrete de Visita de Orientação de Estágio'
                    assunto = (
                        '<h1>Estágios</h1>'
                        '<h2>Lembrete de Visita de Orientação de Estágio</h2>'
                        '<p>Prezado(a) orientador(a), de acordo com as informações enviadas no momento de cadastro do estágio de {}, deve ser realizada e registrada ao menos uma visita durante o período: {} a {}.</p>'
                        '<p>Caso não tenha realizado a visita, por favor, entrar em contato com a concedente para proceder o agendamento.</p>'
                        '<p>Este estágio se iniciou em {} e está prevista para finalizar em {}.</p>'
                        '<p>Informamos que a visita deve ser registrada em formulário próprio disponível no link: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/estagios/modelos-e-formularios/relatorio-de-visita-a-organizacao-concedente/view</p>'
                        '<p>Para registrar a visita, acesse o endereço a seguir: '
                        '<a href="{}accounts/login/?next=/estagios/pratica_profissional/{}/?tab=visitas">Visitas</a>.</p>'
                        '<p>Em caso de dúvidas, procure a Coordenação responsável por estágios no seu Campus.</p>'.format(
                            self.aluno, format_(periodo['inicio']), format_(periodo['fim']), format_(self.data_inicio), format_(self.data_prevista_fim), url_servidor, self.pk
                        )
                    )

                    send_notification(titulo, assunto, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
                    if self.orientador.vinculo.user.email:
                        notificacao = NotificacaoPendencia(
                            pratica_profissional=self,
                            data=datetime.datetime.now(),
                            tipo=NotificacaoPendencia.NOTIFICACAO_VISITA_TRIMESTRAL,
                            notificador=user,
                            email_destinatario=self.orientador.vinculo.user.email,
                            mensagem_enviada='{}<br/>{}'.format(titulo, assunto),
                        )
                        notificacao.save()
                        trimestre_notificado = TrimestreNaoVisitadoNotificado(notificacao=notificacao, inicio=periodo['inicio'], fim=periodo['fim'])
                        trimestre_notificado.save()
                elif self.deve_enviar_notificacao_apos_fim_periodo(periodo):
                    url_servidor = Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')
                    titulo = '[SUAP] Pendência de Registro de Visita'
                    assunto = (
                        '<h1>Estágios</h1>'
                        '<h2>Pendência de Registro de Visita</h2>'
                        '<p>Prezado(a) orientador(a), solicitamos que registre a visita trimestral do estágio de {}.</p>'
                        '<p>Este estágio se iniciou em {} e está prevista para finalizar em {}.</p>'
                        'Essa visita se refere ao trimestre que vai de {} até {}.'
                        '<p>Informamos que a visita deve ser registrada em formulário próprio disponível no link: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/estagios/modelos-e-formularios/relatorio-de-visita-a-organizacao-concedente/view</p>'
                        '<p>Para registrar a visita, acesse o endereço a seguir: '
                        '<a href="{}accounts/login/?next=/estagios/pratica_profissional/{}/?tab=visitas">Visitas</a>.</p>'
                        '<p>Obs.: Caso não tenha realizado a visita, por favor, entrar em contato com a coordenação responsável por estágios para proceder a justificativa de decurso de prazo formal, que também deve ser registrada no SUAP.</p>'
                        '<p>Em caso de dúvidas, procure a Coordenação responsável por estágios no seu Campus.</p>'.format(
                            self.aluno, format_(self.data_inicio), format_(self.data_prevista_fim), format_(periodo['inicio']), format_(periodo['fim']), url_servidor, self.pk
                        )
                    )
                    send_notification(titulo, assunto, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
                    if self.orientador.vinculo.user.email:
                        notificacao = NotificacaoPendencia(
                            pratica_profissional=self,
                            data=datetime.datetime.now(),
                            tipo=NotificacaoPendencia.NOTIFICACAO_VISITA_TRIMESTRAL,
                            notificador=user,
                            email_destinatario=self.orientador.vinculo.user.email,
                            mensagem_enviada='{}<br/>{}'.format(titulo, assunto),
                        )
                        notificacao.save()
                        trimestre_notificado = TrimestreNaoVisitadoNotificado(notificacao=notificacao, inicio=periodo['inicio'], fim=periodo['fim'])
                        trimestre_notificado.save()

    def estagio_esta_dentro_do_periodo(self, periodo):
        return datetime.date.today() <= periodo['fim'] and datetime.date.today() >= periodo['inicio']

    def deve_enviar_primeira_notificacao_de_visita_trimestral(self, periodo):
        def dia_envio_inicial_envio(periodo):
            return periodo['inicio'] + (periodo['fim'] - periodo['inicio']) / 3

        def dia_envio_final_envio(periodo):
            return periodo['inicio'] + 2 * (periodo['fim'] - periodo['inicio']) / 3 - relativedelta(days=1)

        if ((periodo['fim'] - relativedelta(days=20)) == datetime.date.today()) and not TrimestreNaoVisitadoNotificado.objects.filter(
            notificacao__pratica_profissional=self,
            inicio=periodo['inicio'],
            fim=periodo['fim'],
            notificacao__data__date__gte=dia_envio_inicial_envio(periodo),
            notificacao__data__date__lt=dia_envio_final_envio(periodo),
        ).exists():
            return True
        else:
            return False

    def deve_enviar_notificacao_apos_fim_periodo(self, periodo):
        if (
            datetime.date.today() > periodo['fim']
            and not TrimestreNaoVisitadoNotificado.objects.filter(
                notificacao__pratica_profissional=self, inicio=periodo['inicio'], fim=periodo['fim'], notificacao__data__date__gt=datetime.date.today() + relativedelta(days=-10)
            ).exists()
        ):
            return True
        else:
            return False

    def visitas_fora_de_periodo_trimestral(self):
        visitas_em_periodo_trimestral = VisitaPraticaProfissional.objects.none()
        for periodo in self.get_periodos_trimestrais():
            visitas_em_periodo_trimestral |= periodo['visitas']
        return self.visitapraticaprofissional_set.exclude(id__in=visitas_em_periodo_trimestral)

    def notificar_aluno_necessidade_atualizacao_pae(self, data_limite):

        instituicao_sigla = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')

        titulo = '[SUAP] Notificação: Plano de Atividades de Estágio Precisa ser Atualizado'
        mensagem = (
            '<h1>Estágios</h1>'
            '<h2>[SUAP] Notificação: Plano de Atividades de Estágio Precisa ser Atualizado</h2>'
            f'<p>Caro(a) {self.aluno},</p>'
            '<p>Informamos que o Plano de Atividades do seu estágio precisa '
            f'ser renovado até o dia { format_(data_limite) }.</p>'
            f'<p>Você pode entrar em contato com o(a) {instituicao_sigla} (Setor de Estágios/Extensão) '
            'para verificar se essa situação já está sendo resolvida.</p>'
        )

        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.aluno.get_vinculo()])
        email_aluno = self.get_email_aluno()
        if email_aluno:
            notificacao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_NECESSIDADE_ATUALIZACAO_PAE,
                notificador=None,
                email_destinatario=email_aluno,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificacao.save()

    def notificar_supervisor_aluno_necessidade_atualizacao_pae(self, data_limite):
        titulo = '[SUAP] Notificação: Plano de Atividades de Estágio Precisa ser Atualizado'
        mensagem = (
            '<h1>Estágios</h1>'
            '<h2>[SUAP] Notificação: Plano de Atividades de Estágio Precisa ser Atualizado</h2>'
            f'<p>Caro(a) {self.nome_supervisor},</p>'
            f'<p>Informamos que o Plano de Atividades de Estágio do(a) estagiário(a) {self.aluno}, '
            'que se encontra sob sua supervisão, precisa ser renovado.</p>'
            f'<p>A data limite para renovação é: { format_(data_limite) }.</p>'
            '<br>'
            '<p><em>Esta notificação fundamenta-se na cláusula 5ª, art. IV, '
            'do Termo de Ajuste de Conduta nº 293.2013 do Ministério Público do Trabalho/'
            'Procuradoria Regional do Trabalho da 21ª Região, que preconiza que '
            'o Plano de Atividades de Estágio <strong>deve ser</strong> atualizado '
            'a cada 6 (seis) meses.<em></p>'
        )
        if self.email_supervisor:
            send_mail(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.email_supervisor])
            notificacao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_NECESSIDADE_ATUALIZACAO_PAE,
                notificador=None,
                email_destinatario=self.email_supervisor,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificacao.save()

    def notificar_orientador_necessidade_atualizacao_pae(self, data_limite):
        titulo = '[SUAP] Notificação: Plano de Atividades de Estágio Precisa ser Atualizado'
        mensagem = (
            '<h1>Estágios</h1>'
            '<h2>[SUAP] Notificação: Plano de Atividades de Estágio Precisa ser Atualizado</h2>'
            f'<p>Caro(a) {self.orientador},</p>'
            f'<p>Informamos que o Plano de Atividades de Estágio do(a) estagiário(a) {self.aluno}, '
            'que se encontra sob sua orientação, precisa ser renovado.</p>'
            f'<p>A data limite para renovação é: { format_(data_limite) }.</p>'
            '<br>'
            '<p><em>Esta notificação fundamenta-se na cláusula 5ª, art. IV, '
            'do Termo de Ajuste de Conduta nº 293.2013 do Ministério Público do Trabalho/'
            'Procuradoria Regional do Trabalho da 21ª Região, que preconiza que '
            'o Plano de Atividades de Estágio <strong>deve ser</strong> atualizado '
            'a cada 6 (seis) meses.<em></p>'
        )
        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.orientador.vinculo])
        if self.orientador.vinculo.user.email:
            notificacao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_NECESSIDADE_ATUALIZACAO_PAE,
                notificador=None,
                email_destinatario=self.orientador.vinculo.user.email,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificacao.save()

    def notificar_coordenadores_extensao_necessidade_atualizacao_pae(self, data_limite):
        coordenadores = get_coordenadores_estagio(self.aluno)
        coordenadores_nomes = get_coordenadores_nomes(coordenadores)
        coordenadores_emails = get_coordenadores_emails(coordenadores)
        coordenadores_vinculos = get_coordenadores_vinculos(coordenadores)

        titulo = '[SUAP] Notificação: Plano de Atividades de Estágio Precisa ser Atualizado'
        mensagem = (
            '<h1>Estágios</h1>'
            '<h2>[SUAP] Notificação: Plano de Atividades de Estágio Precisa ser Atualizado</h2>'
            f'<p>Caros(as) Coordenadores(as) de Extensão {coordenadores_nomes},</p>'
            f'<p>Informamos que o Plano de Atividades de Estágio do(a) estagiário(a) {self.aluno} '
            f'precisa ser renovado até o dia { format_(data_limite) }.</p>'
            '</br>'
            '<p><em>Esta notificação fundamenta-se na cláusula 5ª, art. IV, '
            'do Termo de Ajuste de Conduta nº 293.2013 do Ministério Público do Trabalho/'
            'Procuradoria Regional do Trabalho da 21ª Região, que preconiza que '
            'o Plano de Atividades de Estágio <strong>deve ser</strong> atualizado '
            'a cada 6 (seis) meses.<em></p>'
        )

        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, coordenadores_vinculos)
        if coordenadores_emails:
            notificacao = NotificacaoPendencia(
                pratica_profissional=self,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_NECESSIDADE_ATUALIZACAO_PAE,
                notificador=None,
                email_destinatario=coordenadores_emails,
                mensagem_enviada='{}<br/>{}'.format(titulo, mensagem),
            )
            notificacao.save()

    def can_change(self, user):
        return not self.data_fim

# (COLOCAR PRAZOS PARA RELATÓRIOS)
# Manual do Supervisor: http://portal.ifrn.edu.br/extensao/estagios-e-egressos/estagios/manuais-de-utilizacao-do-suap
# Caso necessite entrar em contato conosco basta buscar o telefone do campus na página: www.ifrn.edu.br ou no termo de compromisso de estágio, ou, ainda, entrar em contato com o professor orientador, através do seguinte e-mail: (EMAIL DO PROFESSOR ORIENTADOR).

# Desde já agradecemos pela sua contribuição na formação do nosso aluno'


class Atividade(models.ModelPlus):
    CONCEITO_EXCELENTE = 1
    CONCEITO_OTIMO = 2
    CONCEITO_BOM = 3
    CONCEITO_REGULAR = 4
    CONCEITO_RUIM = 5
    CONCEITO_CHOICES = [[CONCEITO_EXCELENTE, 'Excelente'], [CONCEITO_OTIMO, 'Ótimo'], [CONCEITO_BOM, 'Bom'], [CONCEITO_REGULAR, 'Regular'], [CONCEITO_RUIM, 'Ruim']]

    pratica_profissional = models.ForeignKeyPlus(PraticaProfissional, verbose_name='Prática Profissional')
    descricao = models.CharFieldPlus('Descrição', default='', width='800', max_length=1024)

    # FIXME: esses dois próximos atributos servem pra quê? avaliação final do estagiário???
    situacao = models.ForeignKeyPlus(SituacaoAtividade, verbose_name='Situação', null=True, on_delete=models.CASCADE)
    conceito = models.IntegerField('Conceito', choices=CONCEITO_CHOICES, null=True, blank=False)

    class Meta:
        verbose_name = 'Atividade do Estágio'
        verbose_name_plural = 'Relação de Atividades do Estágio'
        ordering = ('pk',)

    def __str__(self):
        return '{}'.format(self.pk)


class EstagioAditivoContratual(models.ModelPlus):
    pratica_profissional = models.ForeignKeyPlus(PraticaProfissional, verbose_name='Prática Profissional')
    descricao = models.CharFieldPlus('Descrição', default='', width='800', max_length=1024, blank=True, null=True)
    aditivo = models.FileFieldPlus('Aditivo', blank=False, max_length=255, upload_to='pratica_profissional/aditivo')
    inicio_vigencia = models.DateFieldPlus('Início da Vingência', blank=False)
    historico = models.TextField('Histórico', null=True)
    tipos_aditivo = models.ManyToManyField('estagios.TipoAditivo', verbose_name='Tipos de Aditivo Contratual', blank=False)

    class Meta:
        verbose_name = 'Aditivo Contratual de Estágio'
        verbose_name_plural = 'Aditivos Contratuais de Estágios'

    def __str__(self):
        lista = []
        for tipo_aditivo in self.tipos_aditivo.all():
            lista.append(str(tipo_aditivo))
        return 'Descrição: {} <br>Tipos: {}'.format(self.descricao, ', '.join(lista))

    def save(self):
        super().save()
        self.pratica_profissional.save()


class TipoAditivo(models.ModelPlus):
    PROFESSOR_ORIENTADOR = 1
    REMUNERACAO = 2
    TRANSPORTE = 3
    OUTROS_BENEFICIOS = 4
    TEMPO = 5
    CARGA_HORARIA = 6
    PLANO_DE_ATIVIDADE = 7
    SUPERVISOR = 8
    HORARIO = 9
    SEGURO = 10
    descricao = models.CharFieldPlus('Decrição')

    class Meta:
        verbose_name = 'Tipo de Aditivo Contratual'
        verbose_name_plural = 'Tipos de Aditivo Contratual'

    def __str__(self):
        return '{}'.format(self.descricao)


class VisitaPraticaProfissional(models.ModelPlus):
    pratica_profissional = models.ForeignKeyPlus(PraticaProfissional, verbose_name='Prática Profissional')
    orientador = models.ForeignKeyPlus(Professor, verbose_name='Orientador')
    data_visita = models.DateFieldPlus('Data da Visita')
    ambiente_adequado = models.BooleanField('Ambiente Adequado', default=False, help_text='O ambiente de trabalho está adequado ao desenvolvimento das atividades do estagiário?')
    ambiente_adequado_justifique = models.TextField(
        'Justificativa para Ambiente Inadequado', default='', blank=True, help_text='Preencher somente em caso de resposta negativa ao quesito anterior.'
    )
    desenvolvendo_atividades_previstas = models.BooleanField(
        'Desenvolvimento Atividades Previstas', default=False, help_text='O estagiário está desenvolvendo as atividades previstas no plano de atividades cadastrado no' ' TCE?'
    )
    desenvolvendo_atividades_nao_previstas = models.BooleanField(
        'Desenvolvimento Atividades Não-Previstas',
        default=False,
        help_text='Existem atividades que estão sendo ' 'desenvolvidas (da competência do estagiário), mas que não estão previstas ' 'no TCE?',
    )
    desenvolvendo_atividades_fora_competencia = models.BooleanField(
        'Desenvolvimento Atividades Fora da Competência', default=False, help_text='Existem atividades que estão sendo desenvolvidas fora das competências do ' 'estagiário?'
    )
    atividades_nao_previstas = models.TextField(
        'Atividades Não-Previstas',
        help_text='Descreva as atividades desenvolvidas que não foram '
        'previstas no plano de atividades, informando ao setor '
        'responsável no IFRN a necessidade da sua atualização.',
        blank=True,
    )
    apoiado_pelo_supervidor = models.BooleanField(
        'Apoiado pelo Supervisor', default=False, help_text='O estagiário está sendo apoiado/orientado/supervisionado pelo supervisor de estágio da concedente?'
    )
    direitos_respeitados = models.BooleanField(
        'Direitos Respeitados', default=False, help_text='Os pagamentos de bolsa e auxílio transporte, bem como o horário de trabalho estão sendo respeitados?'
    )
    direitos_respeitados_especificar = models.TextField(
        'Especificar direitos não respeitados', default='', blank=True, help_text='Preencher somente em caso de resposta negativa ao quesito anterior.'
    )
    aprendizagem_satisfatoria = models.BooleanField(
        'Aprendizagem Satisfatória',
        default=False,
        help_text='De um modo geral, quanto à contribuição ao aprendizado ' 'do estagiário, a prática profissional está ocorrendo de forma satisfatória?',
    )
    informacoes_adicionais = models.TextField(
        'Informações Adicionais',
        help_text='O espaço abaixo é reservado ao registro de informações que '
        'considerar relevantes. (ex.: caso alguma questão não tenha '
        'sido respondida, justificar; ou fazer o relato de outras '
        'informações colhidas durante a visita.)',
        blank=True,
    )
    relatorio = models.FileFieldPlus(
        'Relatório de Visita',
        help_text='Inserir o relatório de visita devidamente assinado. Obs.: Este relatório pode ser gerado pelo sistema após o preenchimento deste formulário. Limite de tamanho do arquivo 2MB.',
        blank=False,
        null=True,
        upload_to='visita_pratica_profissional/relatorio',
        max_file_size=2097152,
    )
    ultimo_editor = models.ForeignKeyPlus('comum.User', verbose_name='Último Usuário a Editar', null=True)

    class Meta:
        verbose_name = 'Visita do Orientador'
        verbose_name_plural = 'Visitas do Orientador'

    def __str__(self):
        return 'Visita realizada em {}'.format(format_(self.data_visita))

    def save(self):
        super().save()
        self.pratica_profissional.save()

    def get_periodo_trimestral(self):
        periodos = self.pratica_profissional.get_periodos_trimestrais()
        for periodo in periodos:
            if self.data_visita >= periodo['inicio'] and self.data_visita <= periodo['fim']:
                return periodo
        return None


class RelatorioSemestralEstagio(models.ModelPlus):
    AVALICAO_CONCEITO_EXCELENTE = 1
    AVALICAO_CONCEITO_BOM = 2
    AVALICAO_CONCEITO_REGULAR = 3
    AVALICAO_CONCEITO_RUIM = 4
    AVALICAO_CONCEITO_PESSIMO = 5
    AVALICAO_CONCEITO_CHOICES = [
        [AVALICAO_CONCEITO_EXCELENTE, 'Excelente'],
        [AVALICAO_CONCEITO_BOM, 'Bom'],
        [AVALICAO_CONCEITO_REGULAR, 'Regular'],
        [AVALICAO_CONCEITO_RUIM, 'Ruim'],
        [AVALICAO_CONCEITO_PESSIMO, 'Péssimo'],
    ]

    pratica_profissional = models.ForeignKeyPlus(PraticaProfissional, verbose_name='Prática Profissional')
    eh_relatorio_do_supervisor = models.BooleanField(editable=False, default=True)

    # data e período do relatório
    data_relatorio = models.DateFieldPlus('Data do Relatório', blank=False, null=True)
    inicio = models.DateFieldPlus('Data Inicial do Período', blank=False, null=True)
    fim = models.DateFieldPlus('Data Final do Período', blank=False, null=True)

    # plano de atividades
    comentarios_atividades = models.TextField('Comentários sobre o desenvolvimento das atividades', null=True, blank=True)
    realizou_outras_atividades = models.BooleanField('Realizou atividades não previstas no Plano de Atividades?', default=False)
    outras_atividades = models.TextField('Em caso afirmativo, descreva as atividades', blank=True, null=True)
    outras_atividades_justificativa = models.TextField('Em caso afirmativo, justifique', blank=True, null=True)

    # relação teoria/prática (somente relatório do estagiário)
    estagio_na_area_formacao = models.BooleanField(
        'Área de Formação', help_text='O estágio foi/está sendo desenvolvido em sua área ' 'de formação?', choices=[[True, 'Sim'], [False, 'Não']], null=True, blank=True
    )
    estagio_contribuiu = models.BooleanField(
        'Contribuição do Estágio', help_text='As atividades desenvolvidas contribuíram para a sua ' 'formação?', choices=[[True, 'Sim'], [False, 'Não']], null=True, blank=True
    )
    aplicou_conhecimento = models.BooleanField(
        'Aplicação do Conhecimento', help_text='Você teve oportunidade de aplicar os conhecimentos ' 'adquiridos no seu Curso?',
        choices=[[True, 'Sim'], [False, 'Não']], null=True, blank=True,
    )

    # avaliação do estágio (somente relatório do estagiário)
    avaliacao_conceito = models.IntegerField(
        'Conceito', help_text='Qual conceito você atribui ao seu estágio no período?', choices=AVALICAO_CONCEITO_CHOICES, null=True, blank=True
    )

    avaliacao_comentarios = models.TextField('Comentários e Sugestões', null=True, blank=True)

    # avaliação de desempenho do estagiário(somente supervisor)
    nota_estagiario = models.IntegerField(
        'Nota do Estagiário',
        choices=[[nota, nota] for nota in range(10 + 1)],
        null=True,
        blank=False,
        help_text='Dê uma nota ao estagiário que avalie seu desempenho como um todo de 0 a 10.',
    )

    # upload do arquivo do relatório
    relatorio = models.FileFieldPlus(
        'Relatório Semestral',
        help_text='O relatório semestral deve estar assinado pelo ' 'Orientador, Estagiário e Supervisor. Tamanho máximo permitido 2MB.',
        blank=False,
        null=True,
        upload_to='relatorio_semestral_estagio/relatorio',
        max_file_size=2097152,
    )

    ultimo_editor = models.ForeignKeyPlus('comum.User', verbose_name='Último Usuário a Editar', null=True)

    def __str__(self):
        return 'Relatório Semestral ({})'.format(self.pk)

    def save(self):
        super().save()
        self.pratica_profissional.save()

    def pode_editar(self, user):
        return self.pratica_profissional.pode_registrar_relatorio_estagiario(user=user, exclude_relatorio_pk=self.pk)

    class Meta:
        verbose_name = 'Relatório de Atividades'
        verbose_name_plural = 'Relatório de Atividades'

    def can_delete(self, user=None):
        return not self.pratica_profissional.data_fim


class RelatorioSemestralEstagioAtividade(models.ModelPlus):
    REALIZADA_SIM = 1
    REALIZADA_NAO = 2
    REALIZADA_CHOICES = [[REALIZADA_SIM, 'Realizada'], [REALIZADA_NAO, 'Não Realizada']]

    NAO_REALIZADA_MOTIVO_TEMPO_INSUFICIENTE = 1
    NAO_REALIZADA_MOTIVO_CONHECIMENTO_INSUFICIENTE = 2
    NAO_REALIZADA_MOTIVO_MUDANCA_PLANO_ATIVIDADES = 3
    NAO_REALIZADA_MOTIVO_SUBSTITUICAO_POR_OUTRA_ATIVIDADE = 4
    NAO_REALIZADA_MOTIVO_OUTRO_MOTIVO = 5
    NAO_REALIZADA_MOTIVO_CHOICES = [
        [NAO_REALIZADA_MOTIVO_TEMPO_INSUFICIENTE, 'Tempo insuficiente'],
        [NAO_REALIZADA_MOTIVO_CONHECIMENTO_INSUFICIENTE, 'Conhecimento insuficiente'],
        [NAO_REALIZADA_MOTIVO_MUDANCA_PLANO_ATIVIDADES, 'Mudança no plano de atividades'],
        [NAO_REALIZADA_MOTIVO_SUBSTITUICAO_POR_OUTRA_ATIVIDADE, 'Substituição por outra atividade'],
        [NAO_REALIZADA_MOTIVO_OUTRO_MOTIVO, 'Outro motivo'],
    ]

    relatorio_semestral = models.ForeignKeyPlus(RelatorioSemestralEstagio, editable=False)
    atividade = models.ForeignKeyPlus(Atividade, editable=False)
    realizada = models.IntegerField('Realização da Atividade', choices=REALIZADA_CHOICES, help_text='A atividade prevista no plano foi realizada?')
    nao_realizada_motivo = models.IntegerField('Motivo', choices=NAO_REALIZADA_MOTIVO_CHOICES, blank=True, null=True)
    nao_realizada_motivo_descricao = models.TextField('Descrição do motivo', blank=True, null=True)

    class Meta:
        verbose_name = 'Avaliação Semestral de Atividade de Estágio'
        verbose_name_plural = 'Avaliações Semestrais de Atividade de Estágio'

    @property
    def is_realizada(self):
        return self.realizada == RelatorioSemestralEstagioAtividade.REALIZADA_SIM

    def __str__(self):
        return 'Avaliação Semestral de Atividade de Estágio({})'.format(self.pk)


class OrientacaoEstagio(models.ModelPlus):
    pratica_profissional = models.ForeignKeyPlus(PraticaProfissional, verbose_name='Prática Profissional')
    orientador = models.ForeignKeyPlus(Professor, verbose_name='Orientador')
    data = models.DateFieldPlus(verbose_name='Data da Reunião de Orientação')
    hora_inicio = models.TimeFieldPlus('Hora de Início')
    local = models.CharFieldPlus('Local')
    descricao = models.TextField('Descrição do Conteúdo da Orientação', blank=True, null=True)

    class Meta:
        ordering = ('-data',)

    def save(self, *args, **kwargs):
        url_servidor = Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')
        titulo = '[SUAP] Orientação de Estágio Agendada'
        texto = (
            '<h1>Orientação de Estágio Agendada</h1>'
            '<p>Foi agendada uma reunião de orientação ({}, {}, em {}) pelo seu orientador {} referente ao '
            'estágio em {}. Para mais detalhes acesse:\n '
            '<a href="{}accounts/login/?next=/estagios/pratica_profissional/{}/?tab=reunioes">Reuniões</a>.</p>'.format(
                format_(self.data),
                self.hora_inicio,
                self.local,
                self.pratica_profissional.orientador,
                self.pratica_profissional.empresa,
                url_servidor,
                self.pratica_profissional.pk,
            )
        )

        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [self.pratica_profissional.aluno.get_vinculo()])
        email_aluno = self.pratica_profissional.get_email_aluno()
        if email_aluno:
            notificacao = NotificacaoPendencia(
                pratica_profissional=self.pratica_profissional,
                data=datetime.datetime.now(),
                tipo=NotificacaoPendencia.NOTIFICACAO_ORIENTACAO_ESTAGIO,
                notificador=self.user,
                email_destinatario=email_aluno,
                mensagem_enviada='{}<br/>{}'.format(titulo, texto),
            )
            notificacao.save()
        super().save()


class NotificacaoPendencia(models.ModelPlus):
    NOTIFICACAO_VISITA_TRIMESTRAL = 1
    NOTIFICACAO_RELATORIO_SEMESTRAL_ALUNO = 2
    NOTIFICACAO_RELATORIO_SEMESTRAL_SUPERVISOR = 3
    NOTIFICACAO_INICIAL = 4
    NOTIFICACAO_APTO_PARA_CONCLUSAO = 5
    NOTIFICACAO_ORIENTACAO_ESTAGIO = 6
    NOTIFICACAO_MATRICULA_IRREGULAR = 7
    NOTIFICACAO_MATRICULA_REGULARIZADA = 8
    NOTIFICACAO_FINAL_MATRICULA_IRREGULAR = 9
    NOTIFICACAO_NECESSIDADE_ATUALIZACAO_PAE = 10

    TIPO_CHOICES = [
        [NOTIFICACAO_VISITA_TRIMESTRAL, 'Notificação  de visita trimestral do orientador.'],
        [NOTIFICACAO_RELATORIO_SEMESTRAL_ALUNO, 'Notificação de relatório semestral do aluno.'],
        [NOTIFICACAO_RELATORIO_SEMESTRAL_SUPERVISOR, 'Notificação de relatório semestral do supervisor.'],
        [NOTIFICACAO_INICIAL, 'Notificação inicial'],
        [NOTIFICACAO_APTO_PARA_CONCLUSAO, 'Notificação de estágio apto para encerramento.'],
        [NOTIFICACAO_ORIENTACAO_ESTAGIO, 'Notificação de orientação de estágio.'],
        [NOTIFICACAO_MATRICULA_IRREGULAR, 'Notificação de matrícula irregular.'],
        [NOTIFICACAO_MATRICULA_REGULARIZADA, 'Notificação de matrícula regularizada.'],
        [NOTIFICACAO_FINAL_MATRICULA_IRREGULAR, 'Notificação de final de matrícula irregular.'],
        [NOTIFICACAO_NECESSIDADE_ATUALIZACAO_PAE, 'Notificação de necessidade de atualização do Plano de Atividades do Estágio.'],
    ]

    pratica_profissional = models.ForeignKeyPlus(PraticaProfissional, verbose_name='Prática Profissional')
    notificador = models.ForeignKeyPlus('comum.User', verbose_name='Notificador', null=True)
    data = models.DateTimeFieldPlus('Data da Notificação')
    tipo = models.IntegerField('Tipo', choices=TIPO_CHOICES)
    email_destinatario = models.TextField('E-mail')
    mensagem_enviada = models.TextField('Mensagem Enviada')

    class Meta:
        ordering = ('-data',)
        verbose_name = 'Notificação de Pendência'
        verbose_name_plural = 'Notificações de Pendências'

    def __str__(self):
        return '{}-{}'.format(self.pk, self.get_tipo_display())


class TrimestreNaoVisitadoNotificado(models.ModelPlus):
    inicio = models.DateTimeFieldPlus('Início')
    fim = models.DateTimeFieldPlus('Fim')
    notificacao = models.ForeignKeyPlus(NotificacaoPendencia, verbose_name='Notificação de Pendência')


class RelatorioSemestralPendenteNotificado(models.ModelPlus):
    inicio = models.DateTimeFieldPlus('Início')
    fim = models.DateTimeFieldPlus('Fim')
    eh_relatorio_do_supervisor = models.BooleanField(editable=False, default=True)
    notificacao = models.ForeignKeyPlus(NotificacaoPendencia, verbose_name='Notificação de Pendência')


class JustificativaVisitaEstagio(models.ModelPlus):
    pratica_profissional = models.ForeignKeyPlus(PraticaProfissional, verbose_name='Estágio')
    inicio = models.DateFieldPlus('Início')
    fim = models.DateFieldPlus('Fim')
    motivos = models.TextField('Informo que a visita à organização concedente não foi realizada pelos seguintes motivos', blank=False)
    outros_acompanhamentos = models.TextField('Foram realizadas outras formas de acompanhamento do (a) aluno (a) sob sua orientação? Se sim, informe quais', blank=True)
    formulario_justificativa = models.FileFieldPlus(
        'Formulário de Justificativa',
        help_text='Esse documento deve ser solicitado ao Coordenador de Estágios, preenchido pelo orientador, e assinado pelo (a) Aluno (a) e Coordenador de Curso/Diretor Acadêmico. Limite de tamanho do arquivo 2MB.',
        blank=False,
        upload_to='justificativa_visita_estagio/relatorio',
        max_file_size=2097152,
    )


class SolicitacaoCancelamentoEncerramentoEstagio(models.ModelPlus):
    AGUARDANDO_RESPOSTA = 1
    DEFERIDA = 2
    INDEFERIDA = 3
    SITUACAO_CHOICES = [[AGUARDANDO_RESPOSTA, 'Aguardando Resposta'], [DEFERIDA, 'Deferida'], [INDEFERIDA, 'Indeferida']]

    estagio = models.ForeignKeyPlus(PraticaProfissional, verbose_name='Prática Profissional', null=True)
    atividade_profissional_efetiva = models.ForeignKeyPlus(AtividadeProfissionalEfetiva, verbose_name='Atividade Profissional Efetiva', null=True)
    user = models.ForeignKeyPlus('comum.User', verbose_name='Solicitante')
    data = models.DateTimeFieldPlus('Data da Solicitação')
    justificativa = models.TextField('Justificativa')
    situacao = models.IntegerField('Situação', choices=SITUACAO_CHOICES, default=AGUARDANDO_RESPOSTA)
    aprendizagem = models.ForeignKeyPlus(Aprendizagem, verbose_name='Aprendizagem', null=True)

    class Meta:
        ordering = ('-data',)
        verbose_name = 'Solicitação de Cancelamento do Encerramento'
        verbose_name_plural = 'Solicitações de Cancelamento do Encerramento'

    def __str__(self):
        return 'Solicitação de Cancelamento de Encerramento de {} ({})'.format(self.get_tipo(), self.pk)

    def save(self):
        if not self.pk:
            self.data = datetime.datetime.now()
        super().save()

    def get_tipo(self):
        if self.estagio:
            return 'Estágio'
        elif self.atividade_profissional_efetiva:
            return 'Atividade Profissional Efetiva'
