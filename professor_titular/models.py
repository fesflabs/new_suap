# -*- coding: utf-8 -*-

import datetime

from dateutil import relativedelta
from django.conf import settings
from django.core.files.storage import default_storage

from djtools.db import models, transaction
from djtools.utils import send_mail, send_notification

PRIVATE_ROOT_DIR = 'private-media/professor_titular'


class ProcessoTitular(models.EncryptedPKModel):
    SEARCH_FIELDS = ['numero', 'protocolo__numero_processo', 'protocolo__numero_documento', 'servidor__nome', 'servidor__matricula']

    '''
    Textos para mensagens de e-mail no processo Titular
    '''
    EMAIL_PROFESSOR_SORTEADO = '''<p>Prezado(a) professor(a) {},</p>
<p>Comunicamos que V.Sa. foi sorteado(a) para participar de banca de avaliação de Professor Titular do docente {} do Instituto Federal de Educação, Ciência e Tecnologia do Rio Grande do Norte (IFRN).</p>
<p>Solicitamos que até o dia {} faça o login no sistema SUAP ([[SITE_URL]]) para ACEITAR ou REJEITAR a participação nesta avaliação. Após esta data o sistema rejeitará automaticamente sua participação.</p>
<p>A avaliação será realizada a distância, em que cada avaliador designado acessará o processo via SUAP e fará sua avaliação individualmente.</p>
<p>A atividade será remunerada por processo avaliado.</p>
<p>Cada avaliador terá um prazo limite de cinco dias para finalizar a avaliação, contados a partir do aceite.</p>
<br />
<p>Caso ainda não tenha definido uma senha de acesso, ou o link de criação da senha estiver com erro, por favor, acesse [[SITE_URL]]/comum/solicitar_trocar_senha/</p>
<p>No campo Usuário, coloque o seu cpf nos dois campos (usuário e cpf). (Usuário tem que ser sem pontuação)</p>
<p>Com isso será reenviado um email para com as instruções para criação da senha de acesso.</p>
<br />
<p>Desde já agradecemos a sua colaboração e colocamo-nos à disposição para esclarecimentos pelo telefone (84) 4005-0766.</p>
<br />
<p>Atenciosamente,</p>
<p>CPPD/IFRN</p>'''.replace(
        '[[SITE_URL]]', settings.SITE_URL
    )
    EMAIL_PROCESSO_SEM_AVALIADOR_RESERVA = '''<p>O processo {} está sem avaliadores reserva. É extermamente necessário o cadastro de mais avaliadores para dar prosseguimento ao processo.</p>
<br />
<p>Por favor, acesse o sistema SUAP [[[SITE_URL]]], procure o menu Recursos Humanos -> CPPD, verifique o processo pendente e adicione mais avaliadores.</p>'''.replace(
        '[[SITE_URL]]', settings.SITE_URL
    )

    EMAIL_PROFESSOR_PERDEU_PRAZO = '''<p>Prezado(a) professor(a) {},</p>
<p>Você perdeu o prazo para aceitação/avaliação do processo {} e não terá mais acesso a este processo. Qualquer ação que você tenha realizado será automaticamente excluída do sistema.</p>
<p>Informamos que esta ação não se aplica a outro(s) processo(s) que eventualmente esteja(m) atribuído(s) a V. Sa, salvo disposição em contrário.</p>
<br />
<p>Atenciosamente,</p>
<p>CPPD/IFRN</p>'''
    '''
    RESOLUÇÃO Nº 1, DE 20 DE FEVEREIRO DE 2014
    Art. 15. A presente Resolução entra em vigor na data de sua publicação e seus efeitos retroagem a 1º de março de 2013.
    '''
    DATA_LEI_RETROATIVIDADE = datetime.date(2013, 3, 1)

    STATUS_APROVADO = 0
    STATUS_REPROVADO = 1
    STATUS_AGUARDANDO_VALIDACAO_CPPD = 2
    STATUS_AGUARDANDO_ENVIO_CPPD = 3
    STATUS_AGUARDANDO_AVALIADORES = 4
    STATUS_AGUARDANDO_AJUSTES_USUARIO = 5
    STATUS_REJEITADO = 6
    STATUS_AGUARDANDO_NOVA_VALIDACAO = 7
    STATUS_AGUARDANDO_ACEITE_AVALIADOR = 8
    STATUS_EM_AVALIACAO = 9
    STATUS_CIENTE_DO_RESULTADO = 10
    STATUS_AGUARDANDO_CIENCIA = 11

    CONCORDA_DEFERIMENTO = 1
    DISCORDA_DEFERIMENTO = 2
    CONCORDA_DEFERIMENTO_CHOICES = [
        [CONCORDA_DEFERIMENTO, 'Concorda com o resultado da avaliação(deferimento/indeferimento)'],
        [DISCORDA_DEFERIMENTO, 'Discorda do resultado da avaliação(deferimento/indeferimento)'],
    ]

    CONCORDA_DATA_RETROATIVIDADE = 1
    DISCORDA_DATA_RETROATIVIDADE = 2
    CONCORDA_DATA_RETROATIVIDADE_CHOICES = [
        [CONCORDA_DATA_RETROATIVIDADE, 'Concorda com a data de retroatividade concedida'],
        [DISCORDA_DATA_RETROATIVIDADE, 'Discorda da data de retroatividade concedida'],
    ]

    STATUS_CHOICES = [
        [STATUS_APROVADO, 'Deferido'],
        [STATUS_REPROVADO, 'Indeferido'],
        [STATUS_AGUARDANDO_VALIDACAO_CPPD, 'Aguardando validação CPPD'],
        [STATUS_AGUARDANDO_ENVIO_CPPD, 'Aguardando envio para CPPD'],
        [STATUS_AGUARDANDO_AVALIADORES, 'Aguardando avaliadores'],
        [STATUS_AGUARDANDO_AJUSTES_USUARIO, 'Aguardando ajustes do usuário'],
        [STATUS_REJEITADO, 'Processo rejeitado'],
        [STATUS_AGUARDANDO_NOVA_VALIDACAO, 'Aguardando nova validação'],
        [STATUS_AGUARDANDO_ACEITE_AVALIADOR, 'Aguardando aceite dos avaliadores'],
        [STATUS_EM_AVALIACAO, 'Em avaliação'],
        [STATUS_CIENTE_DO_RESULTADO, 'Ciente do resultado'],
        [STATUS_AGUARDANDO_CIENCIA, 'Aguardando ciência'],
    ]
    processo_eletronico = models.ForeignKeyPlus('processo_eletronico.Processo', null=True, editable=False)
    protocolo = models.ForeignKeyPlus('protocolo.Processo', blank=True, null=True)
    servidor = models.ForeignKeyPlus('rh.Servidor')
    numero = models.IntegerField('Número do Processo', blank=True, null=True)
    pontuacao = models.DecimalFieldPlus('Pontuação Validada', blank=True, null=True)
    pontuacao_pretendida = models.DecimalFieldPlus('Pontuação Requerida', blank=True, null=True)

    pontuacao_pretendida_grupo_A = models.DecimalFieldPlus(blank=True, null=True)
    pontuacao_pretendida_grupo_B = models.DecimalFieldPlus(blank=True, null=True)
    pontuacao_pretendida_grupo_C = models.DecimalFieldPlus(blank=True, null=True)
    pontuacao_pretendida_grupo_D = models.DecimalFieldPlus(blank=True, null=True)
    pontuacao_pretendida_grupo_E = models.DecimalFieldPlus(blank=True, null=True)
    pontuacao_pretendida_grupo_F = models.DecimalFieldPlus(blank=True, null=True)
    pontuacao_pretendida_grupo_G = models.DecimalFieldPlus(blank=True, null=True)
    pontuacao_pretendida_grupo_H = models.DecimalFieldPlus(blank=True, null=True)

    status = models.IntegerField(choices=STATUS_CHOICES, verbose_name='Situação')
    introducao_relatorio_descritivo = models.TextField(blank=True)
    conclusao_relatorio_descritivo = models.TextField(blank=True)
    itinerario_formacao = models.TextField(blank=True)

    itinerario_formacao_aperfeicoamento_titulacao = models.TextField(blank=True)
    atividade_ensino_orientacao = models.TextField(blank=True)
    atividade_pesquisa_dev_tec_inovacao = models.TextField(blank=True)
    atividade_extensao = models.TextField(blank=True)

    participacao_processo_avaliacao = models.TextField(blank=True)

    revista_cientifica = models.TextField(blank=True)
    membro_comissao_carater_pedagogico = models.TextField(blank=True)
    membro_comissao_elaboracao_ou_revisao_projeto_pedagogico = models.TextField(blank=True)
    organizacao_eventos = models.TextField(blank=True)
    membro_comissao_carater_nao_pedagogico = models.TextField(blank=True)

    exercicio_cargo_direcao_coordenacao = models.TextField(blank=True)
    atividade_aperfeicoamento = models.TextField(blank=True)
    atividade_representacao = models.TextField(blank=True)

    atuacao_docente = models.TextField(blank=True)
    producao_cademica = models.TextField(blank=True)
    prestacao_servicos = models.TextField(blank=True)
    atividade_adm = models.TextField(blank=True)
    titulos_homenagens = models.TextField(blank=True)

    ano = models.IntegerField()
    ano_envio_cppd = models.IntegerField(null=True)

    data_concessao_titulacao_doutor = models.DateFieldPlus('Data de Concessão', blank=False, null=True)
    data_progressaoD404 = models.DateFieldPlus('Data da Progressão/Enquadramento para D404', blank=False, null=True)
    data_avaliacao_desempenho = models.DateFieldPlus('Data da Avaliação de Desempenho', blank=False, null=True)
    data_graduacao_EBTT = models.DateFieldPlus('Data da Graduação para Ingresso no Cargo de Professor de EBTT', blank=False, null=True)

    data_ciencia = models.DateTimeFieldPlus('Data da Ciência', blank=True, null=True, default=None)

    concorda_deferimento = models.IntegerField('Concorda com o deferimento', blank=True, null=True, choices=CONCORDA_DEFERIMENTO_CHOICES)
    concorda_data_retroatividade = models.IntegerField('Concorda com a data de retroatividade', blank=True, null=True, choices=CONCORDA_DATA_RETROATIVIDADE_CHOICES)

    data_finalizacao_processo = models.DateTimeFieldPlus('Data de Finalização do Processo', blank=True, null=True, default=None)

    assinatura_requerimento = models.TextField('Assinatura do requerimento', blank=True, null=True, default="")

    clonado = models.BooleanField("Clonado", default=False)

    objects = models.EncryptedPKModelManager()

    class Meta:
        verbose_name = 'Processo Titular'
        verbose_name_plural = 'Processos Titular'
        permissions = (('pode_validar_processotitular', 'Pode validar Processo Titular'),)

    def __str__(self):
        return 'Processo Titular - {}'.format(self.servidor)

    def ultima_validacao_processo(self):
        retorno = None
        qs = ValidacaoCPPD.objects.filter(processo=self, ajustado=False).order_by('-data')
        if qs.exists():
            retorno = qs[0]
        return retorno

    def pode_selecionar_avaliadores(self):
        retorno = False
        if self.status == self.STATUS_AGUARDANDO_AVALIADORES or self.status == self.STATUS_AGUARDANDO_ACEITE_AVALIADOR or self.status == self.STATUS_EM_AVALIACAO:
            retorno = True
        return retorno

    def pode_ser_validado(self):
        retorno = False
        if self.status == ProcessoTitular.STATUS_AGUARDANDO_VALIDACAO_CPPD or self.status == ProcessoTitular.STATUS_AGUARDANDO_NOVA_VALIDACAO:
            retorno = True
        return retorno

    '''
    editar: o usuário pode editar antes de enviar a CPPD
    '''

    def avaliado_pode_editar(self):
        retorno = False
        if self.status in [self.STATUS_AGUARDANDO_ENVIO_CPPD, self.STATUS_AGUARDANDO_AJUSTES_USUARIO]:
            retorno = True
        return retorno

    '''
    ajustar: o usuário pode ajustar depois que a CPPD avaliou e rejeitou o processo
    OBS: só poderá o avaliado ajustar os campos texto do processo
    '''

    def avaliado_pode_ajustar(self):
        retorno = False
        if self.status == self.STATUS_AGUARDANDO_AJUSTES_USUARIO:
            retorno = True
        return retorno

    def get_pontuacao_pretendida_grupo_A(self):
        retorno = self.pontuacao_pretendida_grupo_A
        if not retorno:
            retorno = 0
        return retorno

    def get_pontuacao_pretendida_grupo_B(self):
        retorno = self.pontuacao_pretendida_grupo_B
        if not retorno:
            retorno = 0
        return retorno

    def get_pontuacao_pretendida_grupo_C(self):
        retorno = self.pontuacao_pretendida_grupo_C
        if not retorno:
            retorno = 0
        return retorno

    def get_pontuacao_pretendida_grupo_D(self):
        retorno = self.pontuacao_pretendida_grupo_D
        if not retorno:
            retorno = 0
        return retorno

    def get_pontuacao_pretendida_grupo_E(self):
        retorno = self.pontuacao_pretendida_grupo_E
        if not retorno:
            retorno = 0
        return retorno

    def get_pontuacao_pretendida_grupo_F(self):
        retorno = self.pontuacao_pretendida_grupo_F
        if not retorno:
            retorno = 0
        return retorno

    def get_pontuacao_pretendida_grupo_G(self):
        retorno = self.pontuacao_pretendida_grupo_G
        if not retorno:
            retorno = 0
        return retorno

    def get_pontuacao_pretendida_grupo_H(self):
        retorno = self.pontuacao_pretendida_grupo_H
        if not retorno:
            retorno = 0
        return retorno

    @classmethod
    def lista_processos(cls, request):
        processos = cls.objects.filter(servidor__id=request.user.get_relacionamento().id)
        return processos

    def get_arquivo_titulacao(self):
        retorno = None
        qs = self.arquivosexigidos_set.filter(tipo=ArquivosExigidos.TITULO_DOUTOR)
        if qs.exists():
            retorno = qs[0]
        return retorno

    def get_arquivo_avaliacao_desempenho(self):
        retorno = None
        qs = self.arquivosexigidos_set.filter(tipo=ArquivosExigidos.TERMO_AVALIACAO_DESEMPENHO)
        if qs.exists():
            retorno = qs[0]
        return retorno

    def get_arquivo_progressao(self):
        retorno = None
        qs = self.arquivosexigidos_set.filter(tipo=ArquivosExigidos.DECLARACAO_DIGPE)
        if qs.exists():
            retorno = qs[0]
        return retorno

    def get_ultima_data_aceite(self):
        datas = ProcessoAvaliador.objects.filter(processo=self, data_aceite__isnull=False).order_by('-data_aceite')
        if datas.exists():
            return datas[0].data_aceite
        else:
            return None

    def get_arquivo_graduacao_ebtt(self):
        retorno = None
        qs = self.arquivosexigidos_set.filter(tipo=ArquivosExigidos.DIPLOMA_GRADUACAO_EBTT)
        if qs.exists():
            retorno = qs[0]
        return retorno

    '''
    Todos os arquivos enviados pelo avaliado ordenados por data de referência
    '''

    def get_arquivos_grupo_pretendido(self):
        return self.arquivo_set.order_by('data_referencia')

    '''
    Retorna o ano do protocolo do processo
    '''

    @property
    def get_ano_protocolo(self):
        if self.ano_envio_cppd:
            tipo_protocolo = self.ano_envio_cppd
        elif self.processo_eletronico:
            tipo_protocolo = self.processo_eletronico.data_hora_criacao.year
        elif self.protocolo:
            tipo_protocolo = self.protocolo.data_cadastro.year

        return tipo_protocolo

    def get_pontuacao_minima(self):
        pontuacao = 150

        ano_protocolo = self.get_ano_protocolo

        # 2014 e 2015 - 100 pontos
        if ano_protocolo in [2014, 2015]:
            pontuacao = 100
        # 2016 - 105 pontos
        if ano_protocolo == 2016:
            pontuacao = 105
        # 2017 - 110 pontos
        if ano_protocolo == 2017:
            pontuacao = 110
        # 2018 - 115 pontos
        if ano_protocolo == 2018:
            pontuacao = 115
        # 2019 - 120 pontos
        if ano_protocolo == 2019:
            pontuacao = 120
        # 2020 - 125 pontos
        if ano_protocolo == 2020:
            pontuacao = 125
        # 2021 - 130 pontos
        if ano_protocolo == 2021:
            pontuacao = 130
        # 2022 - 135 pontos
        if ano_protocolo == 2022:
            pontuacao = 135
        # 2023 - 140 pontos
        if ano_protocolo == 2023:
            pontuacao = 140
        # 2024 - 145 pontos
        if ano_protocolo == 2024:
            pontuacao = 145

        return pontuacao

    '''
    Calcula a pontuação da avaliação
    '''

    def get_pontuacao_avaliacao(self, avaliacao=None, com_corte=True):
        ano_referencia = self.get_ano_protocolo
        if ano_referencia:
            avaliacoes = Avaliacao.objects.filter(processo=self)
            # se for passado uma avaliação, filtra o queryset por ela
            if avaliacao:
                avaliacoes = avaliacoes.filter(pk=avaliacao.pk)

            pontuacao_minima = PontuacaoMinima.objects.filter(ano=ano_referencia)[0]
            pontuacao_exigida = pontuacao_minima.pontuacao_exigida
            qtd_minima_grupos = pontuacao_minima.qtd_minima_grupos
            pontos_grupo = dict()
            pontos_avaliacao = 0
            pontos = 0
            for avaliacao in avaliacoes:
                for item_avaliacao in avaliacao.avaliacaoitem_set.filter(qtd_itens_validado__gt=0):
                    # verificando se a pontuação mínima e qtd mínima de grupos serão as mesmas
                    if item_avaliacao.data_referencia and item_avaliacao.data_referencia and item_avaliacao.data_referencia.year > ano_referencia:
                        # pontuacao_minima = PontuacaoMinima.objects.filter(ano=item_avaliacao.data_referencia.year)[0]
                        if pontuacao_minima:
                            if pontuacao_minima.pontuacao_exigida > pontuacao_exigida:
                                pontuacao_exigida = pontuacao_minima.pontuacao_exigida
                            if pontuacao_minima.qtd_minima_grupos > qtd_minima_grupos:
                                qtd_minima_grupos = pontuacao_minima.qtd_minima_grupos

                    # verificando
                    if item_avaliacao.arquivo.criterio.indicador.grupo.nome in pontos_grupo:
                        pontos_grupo[item_avaliacao.arquivo.criterio.indicador.grupo.nome] += item_avaliacao.pontuacao_validada()
                    else:
                        pontos_grupo[item_avaliacao.arquivo.criterio.indicador.grupo.nome] = item_avaliacao.pontuacao_validada()

                    if com_corte:
                        teto_grupo = item_avaliacao.arquivo.criterio.indicador.grupo.get_teto(pontuacao_minima.ano)
                        if pontos_grupo[item_avaliacao.arquivo.criterio.indicador.grupo.nome] > teto_grupo:
                            pontos_grupo[item_avaliacao.arquivo.criterio.indicador.grupo.nome] = teto_grupo

                    # somando os pontos
                    pontos = sum(pontos_grupo.values())

                pontos_avaliacao += pontos

        return pontos_avaliacao

    def get_data_referencia_retroativa(self):
        data_referencia = None
        if not self.data_concessao_titulacao_doutor or not self.data_progressaoD404:
            return data_referencia

        if self.data_progressaoD404:
            meses = relativedelta.relativedelta(months=24)
            data_referencia = self.data_progressaoD404 + meses

        if self.DATA_LEI_RETROATIVIDADE and data_referencia and self.DATA_LEI_RETROATIVIDADE > data_referencia:
            data_referencia = self.DATA_LEI_RETROATIVIDADE

        if self.data_avaliacao_desempenho and self.data_avaliacao_desempenho > data_referencia:
            data_referencia = self.data_avaliacao_desempenho

        # selecionando os arquivos do processo (apenas dos grupos)
        arquivos_grupo = self.get_arquivos_grupo_pretendido()

        # selecionando pontuação mínima de acordo com o ano da data de referência já setada
        ano_referencia = self.ano
        if data_referencia and data_referencia.year > self.ano:
            ano_referencia = data_referencia.year

        pontuacao_minima = PontuacaoMinima.objects.filter(ano=ano_referencia)[0]
        pontuacao_exigida = pontuacao_minima.pontuacao_exigida
        qtd_minima_grupos = pontuacao_minima.qtd_minima_grupos
        pontos_grupo = dict()
        for arquivo in arquivos_grupo:
            # verificando se a pontuação mínima e qtd mínima de grupos serão as mesmas
            if arquivo.data_referencia and arquivo.data_referencia and arquivo.data_referencia.year > ano_referencia:
                qs_pontuacao_minima = PontuacaoMinima.objects.filter(ano=arquivo.data_referencia.year)
                if not qs_pontuacao_minima:
                    pontuacao_minima = PontuacaoMinima.objects.latest('ano')
                else:
                    pontuacao_minima = qs_pontuacao_minima[0]
                if pontuacao_minima:
                    if pontuacao_minima.pontuacao_exigida > pontuacao_exigida:
                        pontuacao_exigida = pontuacao_minima.pontuacao_exigida
                    if pontuacao_minima.qtd_minima_grupos > qtd_minima_grupos:
                        qtd_minima_grupos = pontuacao_minima.qtd_minima_grupos

            # verificando
            if arquivo.criterio.indicador.grupo.nome in pontos_grupo:
                pontos_grupo[arquivo.criterio.indicador.grupo.nome] += arquivo.nota_pretendida
            else:
                pontos_grupo[arquivo.criterio.indicador.grupo.nome] = arquivo.nota_pretendida

            teto_grupo = arquivo.criterio.indicador.grupo.get_teto(pontuacao_minima.ano)
            if pontos_grupo[arquivo.criterio.indicador.grupo.nome] > teto_grupo:
                pontos_grupo[arquivo.criterio.indicador.grupo.nome] = teto_grupo

            # somando os pontos
            pontos = sum(pontos_grupo.values())

            if len(pontos_grupo) >= qtd_minima_grupos and pontos >= pontuacao_exigida:
                # verificando data de referência
                if data_referencia and arquivo.data_referencia and arquivo.data_referencia > data_referencia:
                    data_referencia = arquivo.data_referencia
                return data_referencia

        return None

    def get_requisitos_minimos_processo(self):
        data_referencia = None
        if not self.data_concessao_titulacao_doutor or not self.data_progressaoD404:
            return data_referencia

        if self.DATA_LEI_RETROATIVIDADE and data_referencia and self.DATA_LEI_RETROATIVIDADE > data_referencia:
            data_referencia = self.DATA_LEI_RETROATIVIDADE

        # selecionando pontuação mínima de acordo com o ano da data de referência já setada
        ano_referencia = self.ano
        if data_referencia and data_referencia.year > self.ano:
            ano_referencia = data_referencia.year

        pontuacao_minima = PontuacaoMinima.objects.filter(ano=ano_referencia)[0]
        for arquivo in self.get_arquivos_grupo_pretendido():
            # verificando se a pontuação mínima e qtd mínima de grupos serão as mesmas
            if arquivo.data_referencia and arquivo.data_referencia.year > ano_referencia:
                qs_pontuacao_minina = PontuacaoMinima.objects.filter(ano=arquivo.data_referencia.year)
                if qs_pontuacao_minina:
                    pontuacao_minima = qs_pontuacao_minina[0]
                else:
                    pontuacao_minima = PontuacaoMinima.objects.latest('ano')

        return pontuacao_minima

    def pontuacao_media_final(self):
        avaliacoes = self.avaliacao_set.filter(status=Avaliacao.FINALIZADA)
        count_avaliacao = avaliacoes.count()
        pontuacao_membros = 0

        for avaliacao in avaliacoes:
            pontuacao_membros += avaliacao.pontuacao_final_individual or 0

        if count_avaliacao > 0:
            return pontuacao_membros / count_avaliacao
        else:
            return 0

    def estado_atual_processo(self):
        pontuacao_minima = self.get_pontuacao_minima()
        if self.pontuacao_media_final() >= pontuacao_minima:
            return ProcessoTitular.STATUS_APROVADO
        else:
            return ProcessoTitular.STATUS_REPROVADO

    @transaction.atomic
    def criar_avaliacao(self, avaliador):
        # criando a avaliação
        avaliacao = Avaliacao()
        avaliacao.processo = self
        avaliacao.avaliador = avaliador
        avaliacao.status = Avaliacao.EM_AVALIACAO
        avaliacao.save()

        # criando os itens que serão avaliados
        for arquivo in self.arquivo_set.all().order_by('data_referencia'):
            avaliacao_item = AvaliacaoItem()
            avaliacao_item.avaliacao = avaliacao
            avaliacao_item.arquivo = arquivo
            avaliacao_item.save()

    @property
    def status_estilizado(self):
        class_css = "status-alert"  # padrao: status a iniciar
        status_display = self.get_status_display()
        if self.pode_ser_validado():
            class_css = "status-alert"
        if self.status == ProcessoTitular.STATUS_APROVADO:
            class_css = "status-success"
        if self.status == ProcessoTitular.STATUS_REPROVADO or self.status == ProcessoTitular.STATUS_REJEITADO:
            class_css = "status-error"
        if self.status == ProcessoTitular.STATUS_CIENTE_DO_RESULTADO:
            class_css = "status-info"
            status_display = '{}: {}'.format(self.get_status_display(), self.get_concorda_deferimento_display())
        return "<span class='status {} text-nowrap-normal'>{}</span>".format(class_css, status_display)

    @property
    def conteudo_a_ser_assinado_do_requerimento(self):
        return '{}{}'.format(self.ano_envio_cppd, self.pontuacao_pretendida)

    @property
    def chave_a_ser_utilizada_na_assinatura_do_requerimento(self):
        return '{}'.format(self.servidor.id)

    def dar_ciencia_resultado(self, opcao_ciencia_deferimento):
        if opcao_ciencia_deferimento:
            if int(opcao_ciencia_deferimento) == 1:
                self.concorda_deferimento = self.CONCORDA_DEFERIMENTO
            else:
                self.concorda_deferimento = self.DISCORDA_DEFERIMENTO

            self.status = self.STATUS_CIENTE_DO_RESULTADO
            self.data_ciencia = datetime.date.today()
            self.save()

    def pode_mostrar_avaliacao(self):
        retorno = False  # Fixme
        if self.status in [self.STATUS_APROVADO, self.STATUS_REPROVADO, self.STATUS_AGUARDANDO_CIENCIA, self.STATUS_CIENTE_DO_RESULTADO]:
            retorno = True
        return retorno

    def pode_mostrar_formulario_ciencia(self):
        retorno = True  # Fixme
        if self.status in [self.STATUS_APROVADO, self.STATUS_REPROVADO]:
            retorno = False
        return retorno

    def finalizar_processo(self):
        situacao = self.estado_atual_processo()
        if situacao == self.STATUS_REPROVADO:
            self.status = self.STATUS_REPROVADO
        else:
            self.status = self.STATUS_APROVADO
        self.data_finalizacao_processo = datetime.date.today()
        self.save()

    '''
    função que retorna os avaliadores do processo
    '''

    def banca_avaliadora_final(self):
        processos_avaliadores = ProcessoAvaliador.objects.filter(processo=self, status=ProcessoAvaliador.AVALIACAO_FINALIZADA).order_by('avaliador__vinculo__pessoa__nome')

        avaliadores = []
        for processo_avaliador in processos_avaliadores:
            avaliadores.append(processo_avaliador.avaliador)

        return avaliadores


class Arquivo(models.EncryptedPKModel):
    processo = models.ForeignKeyPlus('professor_titular.ProcessoTitular', blank=True, null=False, verbose_name='processo associado ao arquivo')
    criterio = models.ForeignKeyPlus('professor_titular.Criterio', blank=True, null=True, verbose_name='critério associado ao arquivo')
    nome = models.CharFieldPlus(max_length=255)
    diretorio = models.CharFieldPlus(max_length=255, unique=True)
    nota_pretendida = models.DecimalFieldPlus(default=0, null=True)
    qtd_itens = models.IntegerField(blank=False, null=True)
    data_referencia = models.DateField('Data de referência', help_text='da', blank=False, null=True)
    tamanho = models.BigIntegerField()
    descricao = models.TextField(blank=True)

    objects = models.EncryptedPKModelManager()

    class Meta:
        ordering = ('criterio__artigo', 'criterio__nome', 'data_referencia')

    def get_qtd_itens(self, avaliador):
        qtd_itens = self.qtd_itens
        avaliacao_item = AvaliacaoItem.objects.filter(arquivo=self, avaliacao__avaliador=avaliador)
        if avaliacao_item.exists() and avaliacao_item[0].qtd_itens_validado is not None and avaliacao_item[0].qtd_itens_validado >= 0:
            qtd_itens = avaliacao_item[0].qtd_itens_validado
        return qtd_itens

    # calcular a nota de cada arquivo dada pelo avaliador de acordo com o número de itens validados
    def get_nota_pretendida(self, avaliador, validada=False):
        if validada:
            return self.get_qtd_itens(avaliador) * self.criterio.pontos
        else:
            return self.qtd_itens * self.criterio.pontos


class ArquivosExigidos(models.EncryptedPKModel):
    TITULO_DOUTOR = 1
    TERMO_AVALIACAO_DESEMPENHO = 2
    DECLARACAO_DIGPE = 3
    DIPLOMA_GRADUACAO_EBTT = 4

    TIPO_DOCUMENTO_EXIGIDO = [
        [TITULO_DOUTOR, 'Título de Doutor'],
        [TERMO_AVALIACAO_DESEMPENHO, 'Termo de Avaliação de Desempenho'],
        [DECLARACAO_DIGPE, 'Declaração DIGPE'],
        [DIPLOMA_GRADUACAO_EBTT, 'Diploma de Graduação para Ingresso em Professor de EBTT'],
    ]

    processo = models.ForeignKeyPlus('professor_titular.ProcessoTitular', blank=True, null=False, verbose_name='Processo Associado ao Arquivo')
    nome = models.CharFieldPlus(max_length=255)
    diretorio = models.CharFieldPlus(max_length=255, unique=True)
    tamanho = models.BigIntegerField()
    tipo = models.IntegerField(choices=TIPO_DOCUMENTO_EXIGIDO)

    objects = models.EncryptedPKModelManager()

    def save(self, *args, **kwargs):
        # selecionando último registro
        ultimo_registro = ArquivosExigidos.objects.filter(processo=self.processo, tipo=self.tipo).order_by('-id')
        if ultimo_registro.exists():
            ultimo_registro = ultimo_registro[0]

            default_storage.delete(ultimo_registro.diretorio)
            ultimo_registro.delete()

        super(self.__class__, self).save(*args, **kwargs)


class Criterio(models.ModelPlus):
    STATUS_ATIVO = 0
    STATUS_INATIVO = 1

    STATUS_CHOICES = [[STATUS_ATIVO, 'Ativo'], [STATUS_INATIVO, 'Inativo']]

    indicador = models.ForeignKeyPlus('professor_titular.Indicador', blank=False, null=False)
    artigo = models.TextField(blank=False)
    nome = models.TextField(blank=False)
    descricao = models.TextField('Descrição', blank=False, null=True)
    status = models.IntegerField(choices=STATUS_CHOICES)
    pontos = models.DecimalFieldPlus()
    unidade = models.ForeignKeyPlus('professor_titular.Unidade', blank=False, null=False, verbose_name='Unidade do critério')
    categoria_memorial_descritivo = models.ForeignKeyPlus('professor_titular.CategoriaMemorialDescritivo', blank=False, null=False)
    num_artigo = models.IntegerField()
    inciso = models.CharFieldPlus(blank=False)
    alinea = models.CharFieldPlus(blank=False)

    class Meta:
        verbose_name = 'Critério'
        verbose_name_plural = 'Critérios'
        ordering = ('num_artigo', 'inciso', 'alinea')

    def __str__(self):
        return '{} - {}'.format(self.nome, self.unidade)

    def tem_arquivo_sem_descricao(self, processo):
        return self.arquivo_set.filter(processo=processo, descricao='').exists()


class Indicador(models.ModelPlus):
    grupo = models.ForeignKeyPlus('professor_titular.Grupo', blank=True, null=True)
    nome = models.CharFieldPlus(max_length=255)
    descricao = models.TextField(blank=False)

    class Meta:
        verbose_name = 'Indicador'
        verbose_name_plural = 'Indicadores'
        ordering = ('pk',)

    def __str__(self):
        return '{}:{}'.format(self.nome, self.descricao)


class Unidade(models.ModelPlus):
    nome = models.CharFieldPlus(max_length=255, unique=True)
    sigla = models.CharFieldPlus(max_length=50)

    class Meta:
        verbose_name = 'Unidade'
        verbose_name_plural = 'Unidades'

    def __str__(self):
        return '{}'.format(self.sigla)


class CategoriaMemorialDescritivo(models.ModelPlus):
    ITINERARIO_FORMACAO_APERFEICOAMENTO_TITULACAO = "c"
    ATIVIDADE_ENSINO_PESQUISA_ORIENTACAO = "d"
    ATIVIDADE_PESQUISA_DEV_TEC_INOVACAO = "e"
    ATIVIDADE_EXTENSAO = "f"
    PARTICIPACAO_PROCESSO_AVALIACAO = "g"
    PARTICIPACAO_REVISTA_CIENTIFICA = "h"
    PARTICIPACAO_MEMBRO_COMISSAO_CARATER_PEDAGOGICO = "i"
    PARTICIPACAO_MEMBRO_COMISSAO_ELABORACAO_OU_REVISAO_PROJETO_PEDAGOGICO = "j"
    PARTICIPACAO_ORGANIZACAO_EVENTOS = "k"
    PARTICIPACAO_MEMBRO_COMISSAO_CARATER_NAO_PEDAGOGICO = "l"
    EXERCICIO_CARGO_DIRECAO_COORDENACAO = "m"
    ATIVIDADE_APERFEICOAMENTO = "n"
    ATIVIDADE_REPRESENTACAO = "o"

    nome = models.CharFieldPlus(max_length=255)
    indice = models.CharFieldPlus(max_length=10)

    class Meta:
        verbose_name = 'Categoria Memorial descritivo'
        verbose_name_plural = 'Categorias Memoriais Descritivos'
        ordering = ('nome',)

    def __str__(self):
        return '{}'.format(self.nome)


class Grupo(models.ModelPlus):
    nome = models.CharFieldPlus(max_length=255)
    percentual = models.DecimalFieldPlus(help_text='Percentual do grupo que compõe a pontuação mínima')

    class Meta:
        verbose_name = 'Grupo de indicadores'
        verbose_name_plural = 'Grupos de indicadores'
        ordering = ('nome',)

    def __str__(self):
        return '{}'.format(self.nome)

    def get_teto(self, ano):
        return (self.percentual * self.pontuacaominima_set.get(ano=ano).pontuacao_exigida) / 100


class PontuacaoMinima(models.ModelPlus):
    qtd_minima_grupos = models.PositiveIntegerField(blank=False, null=True)
    ano = models.IntegerField(blank=False, null=True)
    pontuacao_exigida = models.DecimalFieldPlus(blank=True, null=True, help_text='Pontuação mínima necessária para aprovação no ano em questão')
    grupo = models.ForeignKeyPlus('professor_titular.Grupo', blank=True, null=False, verbose_name='grupo associado à pontuação mínima')

    class Meta:
        unique_together = ('ano', 'grupo')
        verbose_name = 'Pontuação mínima'
        verbose_name_plural = 'Pontuações mínimas'
        ordering = ('ano',)

    def __str__(self):
        return 'Ano: {} - Pontuação Mínima Exigida: {}'.format(self.ano, self.pontuacao_exigida)


class ValidacaoCPPD(models.ModelPlus):
    ACAO_ACEITAR = 0
    ACAO_DEVOLVER = 1
    ACAO_REJEITAR = 2

    ACAO_CHOICES = [[ACAO_ACEITAR, 'Aceitar'], [ACAO_DEVOLVER, 'Devolver'], [ACAO_REJEITAR, 'Rejeitar']]

    TIPO_VALIDACAO_VALIDADO = 1
    TIPO_VALIDACAO_DATA_ERRADA = 2
    TIPO_VALIDACAO_DOCUMENTACAO_NAO_AUTENTICADA = 3
    TIPO_VALIDACAO_DOCUMENTACAO_NAO_CONDIZ_COM_EXIGIDO = 4
    TIPO_VALIDACAO_CHOICE = [
        [TIPO_VALIDACAO_VALIDADO, 'Validado'],
        [TIPO_VALIDACAO_DATA_ERRADA, 'Data errada'],
        [TIPO_VALIDACAO_DOCUMENTACAO_NAO_AUTENTICADA, 'Documentação não autenticada'],
        [TIPO_VALIDACAO_DOCUMENTACAO_NAO_CONDIZ_COM_EXIGIDO, 'Documentação não condiz com o exigido']
    ]

    processo = models.ForeignKeyPlus('professor_titular.ProcessoTitular', blank=True, null=False, verbose_name='Processo Titular')

    data_conclusao_titulacao_validada = models.DateFieldPlus('Data de Conclusão Validada', blank=False, null=True)
    titulacao_status = models.IntegerField('Situação da Titulação', choices=TIPO_VALIDACAO_CHOICE, blank=False, null=True)

    data_graduacao_ebtt_validada = models.DateFieldPlus('Data da Graduação para Ingresso no Cargo de Professor de EBTT Validada', blank=False, null=True)
    graduacao_ebtt_status = models.IntegerField('Situação da Graduação EBTT', choices=TIPO_VALIDACAO_CHOICE, blank=False, null=True)

    data_progressao_validada = models.DateFieldPlus('Data de Progressão Validada', blank=False, null=True)
    progressao_status = models.IntegerField('Situação da Progressão', choices=TIPO_VALIDACAO_CHOICE, blank=False, null=True)

    data_avaliacao_desempenho_validada = models.DateFieldPlus('Data da Avaliação de Desempenho Validada', blank=False, null=True)
    avaliacao_desempenho_status = models.IntegerField('Situação da Avaliações de Desempenho', choices=TIPO_VALIDACAO_CHOICE, blank=False, null=True)

    # formulário de pontuação
    formulario_pontuacao_status = models.IntegerField('Situação do Formulário de Pontuação', blank=False, null=True)

    # situação do relatório descritivo
    relatorio_descritivo_status = models.IntegerField('Situação do Relatório Descritivo', blank=False, null=True)

    validador = models.ForeignKeyPlus('rh.Servidor', related_name='validador')
    acao = models.IntegerField(choices=ACAO_CHOICES)
    motivo_rejeicao = models.CharField('Motivo da Rejeição', max_length=2000)
    data = models.DateTimeFieldPlus(auto_now_add=True, blank=True)
    ajustado = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Validação CPPD'
        verbose_name_plural = 'Validações CPPD'

    def __str__(self):
        return 'Validação do Processo {}'.format(self.processo)


class ProcessoAvaliador(models.ModelPlus):
    DIAS_PARA_ACEITE = 5
    DIAS_PARA_AVALIACAO = 15

    '''
    status
    '''
    EM_ESPERA = 0
    AGUARDANDO_ACEITE = 1
    EM_AVALIACAO = 2
    AVALIACAO_FINALIZADA = 3
    EXCEDEU_TEMPO_ACEITE = 4
    EXCEDEU_TEMPO_AVALIACAO = 5
    REJEITADO_PELO_AVALIADOR = 6

    STATUS_CHOICES = [
        [EM_ESPERA, 'Em espera'],
        [AGUARDANDO_ACEITE, 'Aguardando aceite'],
        [EM_AVALIACAO, 'Aguardando avaliação'],
        [AVALIACAO_FINALIZADA, 'Avaliação finalizada'],
        [EXCEDEU_TEMPO_ACEITE, 'Excedeu tempo de aceite'],
        [EXCEDEU_TEMPO_AVALIACAO, 'Excedeu tempo de avaliação'],
        [REJEITADO_PELO_AVALIADOR, 'Rejeitado pelo avaliador'],
    ]

    AVALIADOR_INTERNO = 'avaliador_interno'
    AVALIADOR_EXTERNO = 'avaliador_externo'
    TIPO_AVALIADOR_CHOICES = [[AVALIADOR_INTERNO, 'Avaliador Interno'], [AVALIADOR_EXTERNO, 'Avaliador Externo']]

    RELACIONADO_PROCESSO_ANALISE = 1
    DE_ORDER_PESSOAL = 2
    DE_ORDER_PROFISSIONAL = 3
    OUTROS = 4
    TIPO_RECUSA_CHOICES = [
        [RELACIONADO_PROCESSO_ANALISE, 'Relacionado ao Processo em Análise'],
        [DE_ORDER_PESSOAL, 'De Ordem Pessoal'],
        [DE_ORDER_PROFISSIONAL, 'De Ordem Profissional'],
        [OUTROS, 'Outros'],
    ]

    processo = models.ForeignKeyPlus('professor_titular.ProcessoTitular', blank=True, null=False, verbose_name='ProcessoTitular')
    avaliador = models.ForeignKeyPlus('rh.Avaliador', blank=True, null=True, verbose_name='Avaliador', related_name='processo_avaliador_titular')
    data_cadastro = models.DateTimeFieldPlus(auto_now_add=True, blank=True)
    data_convite = models.DateTimeFieldPlus('Data do Convite', blank=True, null=True, default=None)
    data_aceite = models.DateTimeFieldPlus('Data do Aceite', blank=True, null=True, default=None)
    status = models.IntegerField('Situação do Avaliador no Processo', choices=STATUS_CHOICES)
    tipo_avaliador = models.CharFieldPlus(choices=TIPO_AVALIADOR_CHOICES)
    tipo_recusa = models.IntegerField(choices=TIPO_RECUSA_CHOICES, blank=True, null=True)
    motivo_recusa = models.CharField('Motivo da Recusa', max_length=2000, blank=True, null=True)
    vinculo_responsavel_cadastro = models.ForeignKeyPlus('comum.Vinculo', null=True, blank=True)

    class Meta:
        verbose_name = 'Avaliador do Processo'
        verbose_name_plural = 'Avaliadores do Processo'
        unique_together = ('processo', 'avaliador')
        permissions = (('pode_avaliar_processotitular', 'Pode avaliar Processo Titular'), ('pode_atualizar_dados_cadastrais', 'Pode atualizar dados cadastrais'))

    def __str__(self):
        return '{} - {}'.format(self.processo, self.avaliador)

    def pode_aceitar_avaliacao(self):
        check_telefone = self.avaliador.vinculo.pessoa.pessoatelefone_set.all()
        if check_telefone and self.avaliador.banco and self.avaliador.numero_agencia and self.avaliador.tipo_conta and self.avaliador.numero_conta:
            return True
        return False

    def aceitar(self):
        self.status = self.EM_AVALIACAO
        self.data_aceite = datetime.date.today()
        self.processo.status = ProcessoTitular.STATUS_EM_AVALIACAO
        self.processo.save()
        self.save()

    @transaction.atomic
    def rejeitar(self, dados):
        self.status = self.REJEITADO_PELO_AVALIADOR
        self.tipo_recusa = dados.get('tipo')
        self.motivo_recusa = dados.get('motivo_recusa')
        self.save()

        '''
        selecionando avaliadores em espera
        '''
        processos = ProcessoAvaliador.objects.filter(processo=self.processo, status=self.EM_ESPERA)
        if self.avaliador.eh_interno():
            processos = processos.filter(status=ProcessoAvaliador.EM_ESPERA, tipo_avaliador=ProcessoAvaliador.AVALIADOR_INTERNO)
        if self.avaliador.eh_externo():
            processos = processos.filter(status=ProcessoAvaliador.EM_ESPERA, tipo_avaliador=ProcessoAvaliador.AVALIADOR_EXTERNO)

        if processos:
            '''
            pegando o primeiro registro em espera para setar o status para "AGUARDANDO ACEITE"
            '''
            processo = processos[0]
            processo.status = ProcessoAvaliador.AGUARDANDO_ACEITE
            processo.data_convite = datetime.datetime.today()
            processo.save()

            '''
            enviando e-mail para o avaliador selecionado
            '''
            assunto = '[SUAP] Avaliação de Processo RSC'
            mensagem = ProcessoTitular.EMAIL_PROFESSOR_SORTEADO.format(
                str(processo.avaliador.vinculo.pessoa.nome), str(processo.processo.servidor.pessoa_fisica.nome), str(processo.data_limite())
            )
            send_notification(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, [processo.avaliador.vinculo])

        else:
            '''
            enviando e-mail para a CPPD informando que não há mais avaliadores reservas para este processo
            '''
            assunto = '[SUAP] Processo RSC sem Avaliador Reserva'
            mensagem = ProcessoTitular.EMAIL_PROCESSO_SEM_AVALIADOR_RESERVA.format(self.processo)

            send_mail(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, ['cppd@ifrn.edu.br'])

    def data_limite(self):
        nova_data = self.data_convite
        dias = self.DIAS_PARA_ACEITE

        if self.data_aceite:
            nova_data = self.data_aceite
            dias = self.DIAS_PARA_AVALIACAO

        falta_dias = True
        cont = 0
        while falta_dias:
            cont = cont + 1
            nova_data = nova_data + datetime.timedelta(days=1)
            if nova_data.weekday() == 5 or nova_data.weekday() == 6:
                nova_data = nova_data + datetime.timedelta(days=1)
                cont = cont - 1
            if cont == dias:
                falta_dias = False

        return nova_data.strftime('%d/%m/%Y')

    def data_limite_display(self):
        if self.status == self.AVALIACAO_FINALIZADA:
            str_data_limite = '-'
        else:
            str_data_limite = '<span class="negrito">Data limite para aceite: </span>{}'.format(self.data_limite())
            if self.data_aceite:
                str_data_limite = '<span class="negrito">Data limite término da avaliação: </span>{}'.format(self.data_limite())
        return str_data_limite

    def situacao_avaliador(self):

        situacao = None
        if self.status == self.EM_ESPERA:
            situacao = '<span class="status status-alert">{}</span>'.format(self.get_status_display())
        if self.status == self.AGUARDANDO_ACEITE:
            situacao = '<span class="status status-info">{}</span>'.format(self.get_status_display())
        elif self.status == self.EM_AVALIACAO or self.status == self.AVALIACAO_FINALIZADA:
            porcentagem = self.calcula_porcentagem_avaliacao()
            situacao = f'''<div class="progress"><p>{porcentagem}</p></div>'''

        elif self.status in [self.REJEITADO_PELO_AVALIADOR, self.EXCEDEU_TEMPO_ACEITE, self.EXCEDEU_TEMPO_AVALIACAO]:
            situacao = '<span class="status status-error">{}</span>'.format(self.get_status_display())

        return situacao

    def calcula_porcentagem_avaliacao(self):
        avaliacao = Avaliacao.objects.filter(processo=self.processo, avaliador=self.avaliador).first()
        porcentagem = 0
        if avaliacao:
            qtd_total_itens_zerados = avaliacao.avaliacaoitem_set.filter(qtd_itens_validado__lte=0).count()
            qtd_total_itens = avaliacao.avaliacaoitem_set.all().count() * 2
            qtd_itens_preenchidos = (
                avaliacao.avaliacaoitem_set.filter(data_referencia__isnull=False).count() + avaliacao.avaliacaoitem_set.filter(qtd_itens_validado__isnull=False).count()
            )
            porcentagem = 100 * qtd_itens_preenchidos / (qtd_total_itens - qtd_total_itens_zerados)

        if int(porcentagem) >= 100:
            porcentagem = 100
        return f'{int(porcentagem)}%'

    def avaliador_excluido_processo(self):
        retorno = None
        if self.status == self.EXCEDEU_TEMPO_ACEITE or self.status == self.EXCEDEU_TEMPO_AVALIACAO or self.status == self.REJEITADO_PELO_AVALIADOR:
            retorno = True
        return retorno

    def avaliador_principal(self):
        retorno = None
        if self.status == self.AGUARDANDO_ACEITE or self.status == self.EM_AVALIACAO or self.status == self.AVALIACAO_FINALIZADA:
            retorno = True
        return retorno

    def avaliador_reserva(self):
        retorno = None
        if self.status == self.EM_ESPERA:
            retorno = True
        return retorno

    @property
    def avaliacao_correspondente(self):
        qs_avaliacao = Avaliacao.objects.filter(processo=self.processo, avaliador=self.avaliador)
        if qs_avaliacao.exists():
            return qs_avaliacao[0]
        return None


class Avaliacao(models.ModelPlus):
    EM_AVALIACAO = 0
    FINALIZADA = 1
    INTERROMPIDA = 3
    DESISTENCIA = 4

    STATUS_CHOICES = [[EM_AVALIACAO, 'Em Avaliação'], [FINALIZADA, 'Finalizada'], [INTERROMPIDA, 'Interrompida'], [DESISTENCIA, 'Desistência']]

    RELACIONADO_PROCESSO_ANALISE = 1
    DE_ORDER_PESSOAL = 2
    DE_ORDER_PROFISSIONAL = 3
    OUTROS = 4
    TIPO_DESISTENCIA_CHOICES = [
        [RELACIONADO_PROCESSO_ANALISE, 'Relacionado ao Processo em Análise'],
        [DE_ORDER_PESSOAL, 'De Ordem Pessoal'],
        [DE_ORDER_PROFISSIONAL, 'De Ordem Profissional'],
        [OUTROS, 'Outros'],
    ]

    AVALIADOR_INTERNO = 'avaliador_interno'
    AVALIADOR_EXTERNO = 'avaliador_externo'
    TIPO_AVALIADOR_CHOICES = [[AVALIADOR_INTERNO, 'Avaliador Interno'], [AVALIADOR_EXTERNO, 'Avaliador Externo']]

    status = models.IntegerField('Situação da Avaliação', choices=STATUS_CHOICES)
    processo = models.ForeignKeyPlus('professor_titular.ProcessoTitular', blank=True, null=False, verbose_name='ProcessoTitular')
    avaliador = models.ForeignKeyPlus('rh.Avaliador', blank=True, null=False, verbose_name='Avaliador', related_name='avaliacao_avaliador_titular')
    motivo_indeferimento = models.CharField('Motivo do Indeferimento', max_length=2000)
    tipo_desistencia = models.IntegerField(choices=TIPO_DESISTENCIA_CHOICES, blank=True, null=True)
    motivo_desistencia = models.CharField('Motivo da Desistência', max_length=2000, blank=True, null=True)
    pontuacao_final_individual = models.DecimalFieldPlus('Pontuação Final Individual do Avaliador', blank=True, null=True)
    data_finalizacao = models.DateTimeFieldPlus('Data da Finalização da Avaliação', blank=True, null=True, default=None)
    avaliacao_paga = models.BooleanField(default=False)
    data_pagamento = models.DateTimeFieldPlus('Data do Pagamento', blank=True, null=True, default=None)
    tipo_avaliador = models.CharFieldPlus(choices=TIPO_AVALIADOR_CHOICES, null=True)

    class Meta:
        verbose_name = 'Avaliação'
        verbose_name_plural = 'Avaliações'

    def pode_avaliar(self):
        retorno = False
        if self.status == self.EM_AVALIACAO:
            retorno = True
        return retorno

    def desistir_avaliacao(self, dados):
        self.status = self.DESISTENCIA
        self.tipo_desistencia = dados.get('tipo')
        self.motivo_desistencia = dados.get('justificativa')
        self.save()

        '''
        selecionando o processo avaliador
        '''
        processoavaliador = ProcessoAvaliador.objects.filter(processo=self.processo, avaliador=self.avaliador)
        if processoavaliador:
            processoavaliador = processoavaliador[0]
            dados_rejeitar = dict()
            dados_rejeitar['tipo'] = dados.get('tipo')
            dados_rejeitar['motivo_recusa'] = dados.get('justificativa')
            processoavaliador.rejeitar(dados_rejeitar)

    def finalizar_avaliacao_titular(self):
        avaliacao = self
        itens_avaliacao = avaliacao.avaliacaoitem_set.all()
        ano_tipo_protocolo = self.processo.get_ano_protocolo

        '''
        verificando se todos os itens já foram preenchidos
        '''
        for item in itens_avaliacao:
            if item.qtd_itens_validado is not None and item.qtd_itens_validado < 0:
                raise Exception('Não é permitido quantidade de items negativo. Por favor, corrija e tente finalizar novamente.')

            if (not item.data_referencia and item.qtd_itens_validado is not None and item.qtd_itens_validado > 0) or item.qtd_itens_validado is None:
                raise Exception('Você não pode finalizar a avaliação sem avaliar todos os quesitos de todos os itens.')

        pontos_grupo = dict()
        for arquivo in self.processo.arquivo_set.all():
            '''
            somando valores por grupo para verificação posterior do teto
            '''
            if arquivo.criterio.indicador.grupo.id in pontos_grupo:
                pontos_grupo[arquivo.criterio.indicador.grupo.id] += arquivo.get_nota_pretendida(self.avaliador, True)
            else:
                pontos_grupo[arquivo.criterio.indicador.grupo.id] = arquivo.get_nota_pretendida(self.avaliador, True)

            if pontos_grupo[arquivo.criterio.indicador.grupo.id] >= arquivo.criterio.indicador.grupo.get_teto(ano_tipo_protocolo):
                pontos_grupo[arquivo.criterio.indicador.grupo.id] = arquivo.criterio.indicador.grupo.get_teto(ano_tipo_protocolo)

        # setando status da avaliação
        avaliacao.status = self.FINALIZADA
        avaliacao.data_finalizacao = datetime.date.today()
        pontuacao_final_individual = sum(pontos_grupo.values())
        avaliacao.pontuacao_final_individual = pontuacao_final_individual
        avaliacao.save()

        '''
        finalizando processo avaliador
        '''
        processo_avaliador = ProcessoAvaliador.objects.filter(processo=avaliacao.processo, avaliador=avaliacao.avaliador, status=ProcessoAvaliador.EM_AVALIACAO)
        if processo_avaliador:
            processo_avaliador = processo_avaliador[0]
            processo_avaliador.status = ProcessoAvaliador.AVALIACAO_FINALIZADA
            processo_avaliador.save()

        # verificar se é a quarta avaliação para setar um status no processo
        avaliacoes = Avaliacao.objects.filter(status=Avaliacao.FINALIZADA, processo=self.processo)
        qtd_avaliacoes = avaliacoes.count()
        if qtd_avaliacoes >= 4:
            processo = avaliacao.processo
            processo.status = ProcessoTitular.STATUS_AGUARDANDO_CIENCIA
            processo.save()

    @property
    def status_estilizado(self):
        class_css = "status-error"  # padrao: status a iniciar
        status_display = self.get_status_display()

        if self.status == Avaliacao.INTERROMPIDA:
            class_css = "status-error"
        if self.status == Avaliacao.DESISTENCIA:
            class_css = "status-error"
        if self.status == Avaliacao.EM_AVALIACAO:
            class_css = "status-success"
        if self.status == Avaliacao.FINALIZADA:
            class_css = "status-success"

        return "<span class='status {} text-nowrap-normal'>{}</span>".format(class_css, status_display)


class AvaliacaoItem(models.ModelPlus):
    avaliacao = models.ForeignKeyPlus('professor_titular.Avaliacao', blank=True, null=False, verbose_name='Avaliação')
    arquivo = models.ForeignKeyPlus('professor_titular.Arquivo', blank=True, null=False, verbose_name='Arquivo')
    data_referencia = models.DateField('Data de Referência Validada', blank=True, null=True)
    qtd_itens_validado = models.IntegerField('Quantidade de Itens Validados', blank=True, null=True)
    justificativa = models.CharField('Justificativa da Avaliação', max_length=2000, blank=True, null=True)

    class Meta:
        verbose_name = 'Avaliação do Item'
        verbose_name_plural = 'Avaliações dos Itens'

    '''
    método que informa se houve alteração na data de referência ou quantidade de itens na avaliação
    '''

    def houve_alteracao_avaliacao(self):
        retorno = False
        if self.data_referencia and self.data_referencia != self.arquivo.data_referencia:
            retorno = True
        if self.qtd_itens_validado is not None and int(self.qtd_itens_validado) != self.arquivo.qtd_itens:
            retorno = True
        return retorno

    '''
    método que informa se o item foi avaliado
    '''

    def item_validado(self):
        validado = False
        if self.qtd_itens_validado is not None and self.qtd_itens_validado >= 0:
            if (self.qtd_itens_validado > 0 and self.data_referencia) or (self.qtd_itens_validado == 0):
                validado = True
        return validado

    '''
    Método que retorna a pontuação validada pelo avaliador
    '''

    def pontuacao_validada(self):
        if self.qtd_itens_validado is not None and self.qtd_itens_validado > 0:
            return self.arquivo.get_nota_pretendida(self.avaliacao.avaliador, True)
        else:
            return None


class CloneArquivoErro(models.ModelPlus):
    ARQUIVO_EXIGIDO = 1
    ARQUIVO = 2
    TIPO_ARQUIVO_CHOICES = [
        [ARQUIVO_EXIGIDO, "Arquivo Exigido"],
        [ARQUIVO, "Arquivo"]
    ]

    tipo_arquivo = models.IntegerFieldPlus("Tipo de Arquivo", choices=TIPO_ARQUIVO_CHOICES)
    nome_arquivo = models.CharFieldPlus("Arquivo")
    processo_titular = models.ForeignKeyPlus("professor_titular.ProcessoTitular", on_delete=models.CASCADE)

    # quando arquivos exigidos
    tipo_documento_exigido = models.CharFieldPlus("Tipo de Documento Exigido", null=True, blank=True)

    # quando arquivos comuns
    indicador = models.CharFieldPlus("Indicador", null=True, blank=True)
    criterio = models.CharFieldPlus("Critério", null=True, blank=True)

    class Meta:
        verbose_name = "Arquivo com problema na clonagem"
        verbose_name_plural = "Arquivos com problema na clonagem"

    def __str__(self):
        return self.nome_arquivo

    def get_localizacao(self):
        if self.tipo_arquivo == self.ARQUIVO_EXIGIDO:
            return self.tipo_documento_exigido
        else:
            return f"{self.indicador} >> {self.criterio}"
